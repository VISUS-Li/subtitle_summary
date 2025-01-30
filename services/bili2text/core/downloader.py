from typing import List, Optional, Dict
import yt_dlp
import re
from pathlib import Path
import sys

from yt_dlp.utils import format_bytes, formatSeconds

from db.service_config import ServiceConfig
from ..config import DOWNLOAD_DIR, MAX_RETRIES, RETRY_DELAY
from .utils import retry_on_failure
from .task_status import TaskStatus
from services.bili2text.core.bilibili import BilibiliAPI
from services.bili2text.core.youtube import YoutubeAPI
from .base import BaseDownloader
from services.bili2text.core.subtitle_manager import SubtitleManager
from db.models.subtitle import SubtitleSource, Platform

class AudioDownloader(BaseDownloader):
    def __init__(self, task_manager=None):
        self.bili_api = BilibiliAPI(
            sessdata="cea96c36%2C1753239359%2C8d5a6%2A12CjB9-mu9IHs0EkKwqRj-qvaM3Edsqx8Hib0vi3RcfxDKF8HcxvWYUrrINWCTous3RioSVnMzUTB3QUZiOTB0WHpNMHNsSFJIb0hLRmM1MEVBY2ZuSFFVVkpFeDYyX3lFYjFETUhjTmdjMTZpOVRoNm1maHFuWDh0X29DdWIzU25LQWlsT0hRZnZRIIEC",
            bili_jct="c4dd6df6d3e0d8fe2fd6554f45801799",
            buvid3="7D9DFB39-938C-8243-A1A1-A9C4508E6F9724117infoc"
        )
        self.download_dir = DOWNLOAD_DIR
        self.task_manager = task_manager
        self.init_bili_api()  # 初始化时立即获取配置
        self.youtube_api = YoutubeAPI()
        self.subtitle_manager = SubtitleManager()

    def init_bili_api(self):
        """从数据库获取最新配置初始化B站API"""
        try:
            db = ServiceConfig()
            cookies = {
                'sessdata': db.get_service_config("bilibili", "sessdata"),
                'bili_jct': db.get_service_config("bilibili", "bili_jct"),
                'buvid3': db.get_service_config("bilibili", "buvid3")
            }
            
            if not all(cookies.values()):
                raise ValueError("B站配置不完整")
            
            self.bili_api = BilibiliAPI(**cookies)
        except Exception as e:
            print(f"初始化B站API失败: {str(e)}")
            self.bili_api = None
            raise

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不合法字符"""
        # 替换Windows文件系统不允许的字符
        filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
        # 替换其他可能导致问题的字符
        filename = re.sub(r'[~！@#￥%……&*（）—+=【】、；''：""，。？]', '_', filename)
        # 将多个下划线替换为单个下划线
        filename = re.sub(r'_+', '_', filename)
        # 限制文件名长度
        if len(filename) > 200:
            filename = filename[:197] + "..."
        return filename.strip('_')

    def _progress_hook(self, d: Dict):
        """yt-dlp下载进度回调"""
        if d['status'] == 'downloading':
            # 计算下载进度百分比
            if 'total_bytes' in d and d['total_bytes'] > 0:
                progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
            else:
                progress = 0
                
            # 构建进度消息
            speed = d.get('speed', 0)
            speed_str = format_bytes(speed) + '/s' if speed else 'N/A'
            
            eta = d.get('eta', 0)
            eta_str = formatSeconds(eta) if eta else 'N/A'
            
            print(
                f"下载进度: {d.get('_percent_str', '0%')} "
                f"速度: {speed_str} "
                f"剩余时间: {eta_str}"
            )
                
        elif d['status'] == 'finished':
            print("下载完成，准备转换格式")
            
        elif d['status'] == 'error':
            print(f"下载失败: {d.get('error', '未知错误')}", file=sys.stderr)

    def _get_existing_file(self, video_id: str) -> Optional[Path]:
        """检查是否存在已下载的文件"""
        # 查找所有以video_id结尾的mp3文件
        existing_files = list(self.download_dir.glob(f"*{video_id}.mp3"))
        if existing_files:
            return existing_files[0]
        return None

    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)
    def _download_audio(self, url: str, task_id: str = None) -> Optional[str]:
        """从URL下载音频"""
        print(f"开始处理音频: {url}")
        
        # 判断是否为YouTube URL
        if 'youtube.com' in url or 'youtu.be' in url:
            video_id = self._extract_youtube_id(url)
        else:
            # 现有的B站逻辑
            bv_match = re.search(r'BV\w+', url)
            if not bv_match:
                raise ValueError("无效的视频URL")
            video_id = bv_match.group()
        
        # 检查是否存在已下载的文件
        existing_file = self._get_existing_file(video_id)
        if existing_file:
            print(f"找到已下载的文件: {existing_file}")
            return str(existing_file)

        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(self.download_dir / '%(title)s-%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'restrictfilenames': True,
            'windowsfilenames': True,
        }

        try:
            if task_id and self.task_manager:
                print(f"[Task {task_id}] Status: {TaskStatus.DOWNLOADING.value}, Message: 开始下载音频...")
                
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                safe_title = self._sanitize_filename(info['title'])
                file_path = self.download_dir / f"{safe_title}-{info['id']}.mp3"
                
                if not file_path.exists():
                    for f in self.download_dir.glob(f"*{info['id']}.mp3"):
                        file_path = f
                        break
                
                print(f"音频下载成功: {file_path}")
                
                if task_id and self.task_manager:
                    print(f"[Task {task_id}] Status: {TaskStatus.DOWNLOADING.value}, Message: 音频下载完成")
                    
                return str(file_path)
                
        except Exception as e:
            print(f"下载失败: {str(e)}")
            if task_id and self.task_manager:
                print(f"[Task {task_id}] Status: {TaskStatus.FAILED.value}, Message: 下载失败: {str(e)}")
            raise

    def _postprocessor_hook(self, task_id: str, d: Dict):
        """后处理进度回调"""
        if not self.task_manager:
            return
            
        if d['status'] == 'started':
            print(f"[Task {task_id}] Status: {TaskStatus.DOWNLOADING.value}, Message: 开始处理: {d.get('postprocessor', '未知处理器')}")
            
        elif d['status'] == 'finished':
            print(f"[Task {task_id}] Status: {TaskStatus.DOWNLOADING.value}, Message: 处理完成: {d.get('postprocessor', '未知处理器')}")

    def download_from_keyword(self, keyword: str, max_results: int = 5) -> List[str]:
        """通过关键词搜索并下载音频"""
        print(f"开始搜索关键词: {keyword}, 最大结果数: {max_results}")

        downloaded_files = []
        videos = self.bili_api.search_videos(keyword, max_results)

        for video in videos:
            try:
                url = f"https://www.bilibili.com/video/{video['bvid']}"
                file_path = self.download_from_url(url)
                if file_path:
                    downloaded_files.append(file_path)
            except Exception as e:
                print(f"下载视频失败 {video['bvid']}: {str(e)}")
                continue

        return downloaded_files

    def _extract_youtube_id(self, url: str) -> str:
        """从YouTube URL中提取视频ID"""
        if 'youtu.be' in url:
            return url.split('/')[-1]
        elif 'youtube.com' in url:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(url)
            return parse_qs(parsed.query)['v'][0]
        raise ValueError("无效的YouTube URL")

    def download_media(self, url: str, task_id: str = None) -> Dict:
        """下载媒体文件"""
        try:
            print(f"开始下载媒体: {url}")
            video_id = self._extract_video_id(url)
            platform = Platform.YOUTUBE if 'youtube' in url.lower() else Platform.BILIBILI
            
            # 检查数据库中是否存在字幕
            existing_subtitle = self.subtitle_manager.get_subtitle(video_id)
            if existing_subtitle:
                print("找到现有字幕，直接返回")
                return {
                    'type': 'subtitle',
                    'content': existing_subtitle['content'],
                    'video_id': video_id,
                    'platform': platform
                }
                        
            # 根据平台选择API
            api = self.youtube_api if platform == Platform.YOUTUBE else self.bili_api
            
            print("获取视频信息...")
            api_video_info = api.get_video_info(video_id)
            
            print("尝试获取官方字幕...")
            subtitle_text = api.get_subtitle(video_id)
            if subtitle_text:
                print("找到官方字幕，保存中...")
                self.subtitle_manager.save_video_info(api_video_info, platform)
                self.subtitle_manager.save_subtitle(
                    video_id=video_id,
                    content=subtitle_text,
                    source=SubtitleSource.OFFICIAL,
                    platform=platform,
                    platform_vid=video_id,
                    language='zh'
                )
                return {
                    'type': 'subtitle',
                    'content': subtitle_text,
                    'video_id': video_id,
                    'platform': platform
                }
            
            print("未找到官方字幕，开始下载音频...")
            # 检查是否有现成的音频文件
            video_info = self.subtitle_manager.get_video_info(platform, video_id)
            if video_info and video_info['audio_path']:
                audio_path = video_info['audio_path']
                if Path(audio_path).exists():
                    print(f"找到现有音频文件: {audio_path}")
                    return {
                        'type': 'audio',
                        'content': audio_path,
                        'video_id': video_id,
                        'platform': platform
                    }
            audio_path = str(self.download_dir / f'{video_id}.mp3')
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'outtmpl': audio_path,
                'quiet': True,
                'progress_hooks': [self._progress_hook]
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            print(f"音频下载完成: {audio_path}")
            print("保存视频信息...")
            
            self.subtitle_manager.save_video_info(
                api_video_info, 
                platform,
                audio_path=audio_path
            )
            
            return {
                'type': 'audio',
                'content': audio_path,
                'video_id': video_id,
                'platform': platform
            }

        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def batch_download(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """实现批量下载抽象方法"""
        results = []
        try:
            # 根据平台选择搜索API
            if 'youtube' in keyword.lower():
                videos = self.youtube_api.search_videos(keyword, max_results)
                base_url = 'https://youtu.be/'
            else:
                videos = self.bili_api.search_videos(keyword, max_results)
                base_url = 'https://www.bilibili.com/video/'

            for video in videos:
                video_id = video.get('id') or video.get('bvid')
                url = f"{base_url}{video_id}"
                result = self.download_media(url)
                results.append({
                    'video_id': video_id,
                    'title': video.get('title'),
                    'result': result
                })
        except Exception as e:
            if self.task_manager:
                self.task_manager.add_log(None, "ERROR", f"批量下载失败: {str(e)}")
        return results

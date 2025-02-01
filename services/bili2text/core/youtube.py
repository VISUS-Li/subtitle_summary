import sys
from typing import List, Dict, Optional
import random
import time
import os

import yt_dlp

from db.service_config import ServiceConfig
from .utils import retry_on_failure
from ..config import MAX_RETRIES, RETRY_DELAY


class YoutubeAPI:
    def __init__(self):
        # 基础配置
        self.base_opts = {
            'verbose': True,
            'no_warnings': False,
            # 调整参数名称和格式
            'sleep_interval_requests': 3,  # 请求间隔最小时间(秒)
            'ratelimit': 800000,  # 修改这里：使用数字而不是字符串 '800K'
            # 重试配置
            'retries': 2,  # 重试次数
            'fragment_retries': 2,  # 分片下载重试次数
            'retry_sleep': 10,  # 重试等待时间(秒)
            # 添加代理支持(如果需要)
            # 'proxy': 'socks5://127.0.0.1:1080',
        }

        # 视频信息获取配置
        self.info_opts = {
            **self.base_opts,
            'skip_download': True,
            'extract_flat': True,
        }

        # 字幕下载配置
        self.subtitle_opts = {
            **self.base_opts,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'best',  # 使用best格式
            'sleep_interval_subtitles': 30,
        }

        # 音频下载配置
        self.audio_opts = {
            **self.base_opts,
            'format': 'bestaudio/best',
            'extract_audio': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'restrictfilenames': True,
            'windowsfilenames': True,
        }

        self._set_cookies2yt_dlp()

    def _set_cookies2yt_dlp(self):
        """更新cookies配置，生成标准的 Netscape cookie 文件"""
        try:
            db = ServiceConfig()
            cookie_file = "youtube_cookies.txt"

            # 获取完整的cookie配置
            cookie_data = db.get_service_config("youtube", "cookie_data")

            if cookie_data:
                # 如果存在旧的cookie文件，删除它
                if os.path.exists(cookie_file):
                    os.remove(cookie_file)

                # 直接写入完整的cookie数据
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    f.write(cookie_data)

                # 设置 cookiefile 参数
                # self.base_opts['cookiefile'] = cookie_file

            elif 'cookiefile' in self.base_opts:
                # 如果没有cookie数据但存在旧的cookie文件，删除它
                if os.path.exists(self.base_opts['cookiefile']):
                    os.remove(self.base_opts['cookiefile'])
                del self.base_opts['cookiefile']
            return self.base_opts

        except Exception as e:
            print(f"从配置初始化YouTube API失败: {str(e)}")
            return None

    def _normalize_language_code(self, lang_code: str) -> Optional[str]:
        """将各种语言代码标准化为 'zh' 或 'en'"""
        lang_code = lang_code.lower().split('-')[0]  # 提取基础语言代码

        # 中文变体映射
        if lang_code in ['zh', 'zho', 'chi']:
            return 'zh'
        # 英文变体映射
        elif lang_code in ['en', 'eng']:
            return 'en'
        return None

    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)
    def get_subtitle(self, video_id: str) -> Optional[str]:
        """使用yt-dlp获取YouTube字幕"""
        try:
            print(f"尝试获取YouTube字幕: {video_id}")
            self._set_cookies2yt_dlp()
            with yt_dlp.YoutubeDL(self.subtitle_opts) as ydl:
                info = ydl.extract_info(video_id, download=False)
                if not info:
                    print(f"获取视频信息失败: {video_id}")
                    return None
                    
                subs = info.get('subtitles') or info.get('automatic_captions')
                if not subs:
                    print(f"未找到字幕: {video_id}")
                    return None

                # 对所有可用字幕进行语言代码标准化，并保留最后一个出现的字幕
                normalized_subs = {}
                # 保持原始顺序，直接遍历
                for lang_code in subs.keys():
                    normalized_lang = self._normalize_language_code(lang_code)
                    if normalized_lang:
                        normalized_subs[normalized_lang] = subs[lang_code]

                # 按优先级尝试获取字幕
                for lang in ['zh', 'en']:
                    if lang in normalized_subs:
                        print(f"找到{lang}语言字幕")
                        sub = normalized_subs[lang][-1]  # 选择最佳格式
                        return self._download_subtitle(sub['url'])

                print(f"未找到支持的语言字幕: {video_id}")
                return None
        except Exception as e:
            error_msg = f"获取YouTube字幕失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def _download_subtitle(self, url: str) -> str:
        """下载字幕文件"""
        try:
            print(f"开始下载字幕: {url}")
            self._set_cookies2yt_dlp()
            with yt_dlp.YoutubeDL() as ydl:
                subtitle_data = ydl.urlopen(url).read().decode('utf-8')
                print("字幕下载完成")
                return subtitle_data
        except Exception as e:
            error_msg = f"下载字幕文件失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def get_video_info(self, url: str) -> dict:
        """获取视频信息"""
        try:
            print(f"获取视频信息: {url}")
            self._set_cookies2yt_dlp()
            with yt_dlp.YoutubeDL(self.info_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            error_msg = f"获取视频信息失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def search_videos(self, keyword: str, max_results: int = 200, batch_size: int = 20) -> List[Dict]:
        """使用yt-dlp分批搜索YouTube视频
        
        Args:
            keyword: 搜索关键词
            max_results: 最大结果数量
            batch_size: 每批次处理的视频数量，默认20个
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            print(f"搜索YouTube视频: {keyword}, 目标数量: {max_results}")
            videos = []
            remaining = max_results

            # 在基础配置上添加搜索特有的配置
            search_opts = self.info_opts.copy()

            while remaining > 0:
                current_batch = min(batch_size, remaining)
                search_url = f"ytsearch{current_batch}:{keyword}"

                print(f"获取下一批次视频，数量: {current_batch}")
                self._set_cookies2yt_dlp()
                with yt_dlp.YoutubeDL(search_opts) as ydl:
                    results = ydl.extract_info(search_url, download=False)

                    if results and 'entries' in results:
                        batch_videos = []
                        for entry in results['entries']:
                            if entry.get('id'):  # 确保有视频ID
                                batch_videos.append({
                                    'id': entry.get('id'),
                                    'title': entry.get('title'),
                                    'duration': entry.get('duration'),
                                    'view_count': entry.get('view_count'),
                                    'uploader': entry.get('uploader'),
                                    'description': entry.get('description')
                                })

                        videos.extend(batch_videos)
                        print(f"本批次成功获取 {len(batch_videos)} 个视频")

                        # 如果本批次获取的视频数量少于预期，说明可能已经没有更多结果
                        if len(batch_videos) < current_batch:
                            print("没有更多视频结果")
                            break

                        remaining -= len(batch_videos)

                        # 批次之间添加延迟，避免频繁请求
                        if remaining > 0:
                            delay = random.uniform(10, 20)  # 10-20秒随机延迟
                            print(f"等待 {delay:.1f} 秒后继续下一批次")
                            time.sleep(delay)
                    else:
                        print("未找到视频结果")
                        break

            print(f"搜索完成，共找到 {len(videos)} 个视频")
            return videos

        except Exception as e:
            error_msg = f"YouTube搜索失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def download_audio(self, url: str, output_path: str) -> str:
        """下载音频"""
        try:
            # 移除 .mp3 扩展名，因为 yt-dlp 会自动添加正确的扩展名
            base_path = output_path.replace('.mp3', '')
            opts = {
                **self.audio_opts,
                'outtmpl': f'{base_path}.%(ext)s',  # 确保正确的输出格式
            }
            print(f"开始下载音频: {url}")
            self._set_cookies2yt_dlp()

            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    ydl.extract_info(url, download=True)
                    return output_path
                except Exception as e:
                    if "EOF occurred in violation of protocol" in str(e):
                        raise Exception(f"SSL连接错误: {str(e)}")
                    raise
        except Exception as e:
            raise Exception(f"下载音频失败: {str(e)}")

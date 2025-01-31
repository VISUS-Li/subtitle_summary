import re
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional

import yt_dlp

from db.models.subtitle import SubtitleSource, Platform
from services.bili2text.core.bilibili import BilibiliAPI
from services.bili2text.core.subtitle_manager import SubtitleManager
from services.bili2text.core.utils import retry_on_failure
from services.bili2text.core.youtube import YoutubeAPI
from services.bili2text.config import DOWNLOAD_DIR, MAX_RETRIES, RETRY_DELAY


class AudioDownloader:
    """音频下载器,负责从各平台下载音频"""

    def __init__(self):
        """初始化下载器"""
        self.download_dir = DOWNLOAD_DIR
        self.bili_api = BilibiliAPI()
        self.youtube_api = YoutubeAPI()
        self.subtitle_manager = SubtitleManager()

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名,移除不合法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 清理后的文件名
        """
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

    def _get_existing_file(self, video_id: str) -> Optional[Path]:
        """检查是否存在已下载的文件
        
        Args:
            video_id: 视频ID
            
        Returns:
            Optional[Path]: 文件路径,不存在则返回None
        """
        existing_files = list(self.download_dir.glob(f"*{video_id}.mp3"))
        if existing_files:
            return existing_files[0]
        return None

    def _extract_video_id(self, url: str) -> str:
        """从URL中提取视频ID
        
        Args:
            url: 视频URL
            
        Returns:
            str: 视频ID
            
        Raises:
            ValueError: URL格式无效
        """
        if 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
            if 'youtu.be' in url:
                return url.split('/')[-1]
            else:
                pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
                match = re.search(pattern, url)
                if not match:
                    raise ValueError("无效的YouTube URL")
                return match.group(1)
        else:
            bv_match = re.search(r'BV\w+', url)
            if not bv_match:
                raise ValueError("无效的B站URL")
            return bv_match.group()

    def _verify_downloaded_file(self, file_path: str) -> bool:
        """验证下载的文件是否有效
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否有效
        """
        # 获取不带扩展名的文件路径
        file_base = os.path.splitext(file_path)[0]
        
        # 检查目录下是否存在以该基础名开头的其他文件
        dir_path = os.path.dirname(file_path)
        base_name = os.path.basename(file_base)
        
        for f in os.listdir(dir_path):
            if f.startswith(base_name):
                full_path = os.path.join(dir_path, f)
                if full_path != file_path:  # 如果不是目标mp3文件
                    print(f"发现同名临时文件: {f}")
                    os.remove(full_path)  # 删除临时文件
        
        # 检查目标mp3文件
        if not os.path.exists(file_path):
            return False
        if os.path.getsize(file_path) == 0:
            # 删除空文件
            os.remove(file_path)
            return False
        
        return True

    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)
    def download_media(self, url: str) -> Dict:
        """下载媒体文件
        
        Args:
            url: 视频URL
            
        Returns:
            Dict: 下载结果,包含:
                - type: 'subtitle' 或 'audio'
                - content: 字幕内容或音频文件路径
                - video_id: 视频ID
                - platform: 平台
                
        Raises:
            Exception: 下载失败
        """
        try:
            print(f"开始下载媒体: {url}")
            video_id = self._extract_video_id(url)
            platform = Platform.YOUTUBE if 'youtube' in url.lower() else Platform.BILIBILI

            # 1. 检查数据库中是否存在字幕
            existing_subtitle = self.subtitle_manager.get_subtitle(video_id)
            if existing_subtitle:
                print("找到现有字幕,直接返回")
                return {
                    'type': 'subtitle',
                    'content': existing_subtitle['content'],
                    'video_id': video_id,
                    'platform': platform
                }

            # 2. 根据平台选择API
            api = self.youtube_api if platform == Platform.YOUTUBE else self.bili_api

            # 3. 获取视频信息
            print("获取视频信息...")
            api_video_info = api.get_video_info(video_id)

            # 4. 尝试获取官方字幕
            print("尝试获取官方字幕...")
            subtitle_text = api.get_subtitle(video_id)
            if subtitle_text:
                print("找到官方字幕,保存中...")
                self.subtitle_manager.save_video_info(api_video_info, platform)
                self.subtitle_manager.save_subtitle(
                    video_id=video_id,
                    content=subtitle_text,
                    timed_content=None,
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

            # 5. 未找到字幕,下载音频
            print("未找到官方字幕,准备下载音频...")

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

            # 下载新的音频文件
            audio_path = str(self.download_dir / f'{video_id}.mp3')
            # 先检查并删除可能存在的同名文件
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            try:
                audio_path = api.download_audio(url, audio_path)
                # 验证下载的文件
                if not self._verify_downloaded_file(audio_path):
                    raise Exception("下载完成但文件无效")
                
                print(f"音频下载完成: {audio_path}")
                
                # 保存视频信息
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
                # 如果下载失败，清理可能存在的不完整文件
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                raise Exception(f"音频下载失败: {str(e)}")

        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def search_videos(self, keyword: str, platform: Platform, max_results: int = 200) -> List[Dict]:
        """搜索视频
        
        Args:
            keyword: 搜索关键词
            platform: 平台 (BILIBILI 或 YOUTUBE)
            max_results: 最大结果数量
            
        Returns:
            List[Dict]: 搜索结果列表
            
        Raises:
            ValueError: 平台不支持
            Exception: 搜索失败
        """
        try:
            print(f"在{platform.value}上搜索视频: {keyword}")

            if platform == Platform.YOUTUBE:
                if not self.youtube_api:
                    raise ValueError("YouTube API未初始化")
                return self.youtube_api.search_videos(keyword, max_results)

            elif platform == Platform.BILIBILI:
                if not self.bili_api:
                    raise ValueError("B站API未初始化")
                return self.bili_api.search_videos(keyword, max_results)

            else:
                raise ValueError(f"不支持的平台: {platform}")

        except Exception as e:
            error_msg = f"搜索视频失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

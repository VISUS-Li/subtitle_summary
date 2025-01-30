from typing import List, Dict, Optional
import yt_dlp
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from .base import BaseVideoAPI
from ..config import MAX_RETRIES, RETRY_DELAY
from .utils import retry_on_failure
import sys

class YoutubeAPI(BaseVideoAPI):
    def __init__(self):
        self.ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitlesformat': 'best',
            'quiet': True
        }

    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)
    def get_subtitle(self, video_id: str) -> Optional[str]:
        """使用yt-dlp获取YouTube字幕"""
        try:
            print(f"尝试获取YouTube字幕: {video_id}")
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(video_id, download=False)
                subs = info.get('subtitles') or info.get('automatic_captions')
                
                if not subs:
                    print(f"未找到字幕: {video_id}")
                    return None
                
                # 优先选择中文和英文字幕
                for lang in ['zh', 'zh-Hans', 'zh-CN', 'en', 'en-US']:
                    if lang in subs:
                        print(f"找到{lang}语言字幕")
                        sub = subs[lang][-1]  # 选择最佳格式
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
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                subtitle_data = ydl.urlopen(url).read().decode('utf-8')
                print("字幕下载完成")
                return subtitle_data
        except Exception as e:
            error_msg = f"下载字幕文件失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)        
    def search_videos(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """搜索YouTube视频"""
        try:
            print(f"搜索YouTube视频: {keyword}, 最大结果数: {max_results}")
            ydl_opts = {
                'extract_flat': True,
                'quiet': True,
                'default_search': f'ytsearch{max_results}:'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(keyword, download=False)
                videos = [{
                    'id': entry['id'],
                    'title': entry['title'],
                    'url': entry['url'],
                    'duration': entry.get('duration'),
                    'view_count': entry.get('view_count')
                } for entry in result['entries']]
                
                print(f"搜索完成，找到 {len(videos)} 个视频")
                return videos
                
        except Exception as e:
            error_msg = f"搜索YouTube视频失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def get_video_info(self, video_id: str) -> Dict:
        """获取视频详细信息"""
        try:
            print(f"获取YouTube视频信息: {video_id}")
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(video_id, download=False)
                print(f"成功获取视频信息: {video_id}")
                return info
        except Exception as e:
            error_msg = f"获取视频信息失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise 
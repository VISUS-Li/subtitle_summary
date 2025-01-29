from typing import List, Dict, Optional
import yt_dlp
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from .base import BaseVideoAPI
from ..config import MAX_RETRIES, RETRY_DELAY
from .utils import retry_on_failure

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
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(video_id, download=False)
                subs = info.get('subtitles') or info.get('automatic_captions')
                
                if not subs:
                    return None
                
                # 优先选择中文和英文字幕
                for lang in ['zh', 'zh-Hans', 'zh-CN', 'en']:
                    if lang in subs:
                        sub = subs[lang][-1]  # 选择最佳格式
                        return self._download_subtitle(sub['url'])
        except Exception as e:
            print(f"获取YouTube字幕失败: {str(e)}")
            return None

    def _download_subtitle(self, url: str) -> str:
        """下载字幕文件"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                # 直接获取字幕内容而不是下载
                subtitle_data = ydl.urlopen(url).read().decode('utf-8')
                return subtitle_data
        except Exception as e:
            print(f"下载字幕文件失败: {str(e)}")
            return None

    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)        
    def search_videos(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """搜索YouTube视频"""
        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
            'default_search': f'ytsearch{max_results}:'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(keyword, download=False)
            return [{
                'id': entry['id'],
                'title': entry['title'],
                'url': entry['url'],
                'duration': entry.get('duration'),
                'view_count': entry.get('view_count')
            } for entry in result['entries']]

    def get_video_info(self, video_id: str) -> Dict:
        """获取视频详细信息"""
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(video_id, download=False) 
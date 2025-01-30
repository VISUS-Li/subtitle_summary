from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import re

class BaseVideoAPI(ABC):
    """视频平台API基类"""
    
    @abstractmethod
    def search_videos(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """搜索视频抽象方法"""
        pass
    
    @abstractmethod
    def get_subtitle(self, video_id: str) -> Optional[str]:
        """获取字幕抽象方法"""
        pass
    
    @abstractmethod
    def get_video_info(self, video_id: str) -> Dict:
        """获取视频信息抽象方法"""
        pass

class BaseDownloader(ABC):
    """下载器基类"""
    
    @abstractmethod
    def download_media(self, url: str, task_id: str = None) -> Dict:
        """下载媒体文件抽象方法"""
        pass
    
    @abstractmethod
    def batch_download(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """批量下载抽象方法"""
        pass

    def _extract_video_id(self, url: str) -> str:
        """从URL中提取视频ID"""
        if 'youtube' in url.lower() or 'youtu.be' in url.lower():
            # YouTube URL格式: 
            # https://www.youtube.com/watch?v=VIDEO_ID 或
            # https://youtu.be/VIDEO_ID
            if 'youtu.be' in url:
                return url.split('/')[-1]
            else:
                pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
                match = re.search(pattern, url)
                if not match:
                    raise ValueError("无效的YouTube URL")
                return match.group(1)
        else:
            # B站URL格式: https://www.bilibili.com/video/BV1xx411c7mD
            bv_match = re.search(r'BV\w+', url)
            if not bv_match:
                raise ValueError("无效的B站URL")
            return bv_match.group() 
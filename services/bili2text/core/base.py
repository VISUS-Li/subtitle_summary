from abc import ABC, abstractmethod
from typing import List, Dict, Optional

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
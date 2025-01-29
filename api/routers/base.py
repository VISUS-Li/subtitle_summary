from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from fastapi import WebSocket, BackgroundTasks
from pydantic import BaseModel

class VideoResponse(BaseModel):
    """统一的视频响应模型"""
    id: str  # 视频ID (BV号或YouTube ID)
    title: str
    text: str
    type: str  # 'subtitle' 或 'audio'

class VideoProcessor(ABC):
    """视频处理器基类"""
    
    @abstractmethod
    async def search_videos(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> List[Dict]:
        """搜索视频"""
        pass
    
    @abstractmethod
    async def get_video_text(
        self, 
        video_id: str, 
        background_tasks: BackgroundTasks
    ) -> Dict[str, str]:
        """获取视频文本(异步任务)"""
        pass
    
    @abstractmethod
    async def process_video(self, video_id: str) -> VideoResponse:
        """直接处理单个视频"""
        pass
        
    @abstractmethod
    async def batch_process(
        self,
        keyword: str,
        max_results: int,
        background_tasks: BackgroundTasks
    ) -> Dict[str, str]:
        """批量处理视频"""
        pass
        
    @abstractmethod
    async def handle_websocket(
        self,
        websocket: WebSocket,
        task_id: str
    ) -> None:
        """处理WebSocket连接"""
        pass 
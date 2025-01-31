from fastapi import APIRouter, HTTPException, WebSocket, BackgroundTasks
from pydantic import BaseModel

from db.models.subtitle import Platform
from services.bili2text.core.video_processor import VideoProcessor

router = APIRouter(prefix="/youtube", tags=["youtube"])


class VideoResponse(BaseModel):
    id: str
    title: str
    text: str
    type: str


class YouTubeVideoResponse(BaseModel):
    id: str
    title: str
    text: str
    type: str  # 'subtitle' 或 'audio'


# 全局处理器实例
video_processor = None


def init_youtube_processor(videoprocessor: VideoProcessor):
    """初始化YouTube处理器"""
    global video_processor
    try:
        video_processor = videoprocessor
        return True
    except Exception as e:
        print(f"初始化YouTube处理器失败: {str(e)}")
        return False


# API路由定义
@router.post("/search")
async def search_videos(keyword: str, page: int = 1, page_size: int = 20):
    """搜索YouTube视频"""
    if not video_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    return await video_processor.search_videos(keyword, page_size)


@router.post("/video/{video_id}")
async def get_video_text(video_id: str, background_tasks: BackgroundTasks):
    """获取视频文本"""
    if not video_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    return await video_processor.process_single_video(
        video_id,
        Platform.YOUTUBE
    )


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket连接处理"""
    if not video_processor:
        await websocket.close(code=1000)
        return
    await video_processor.handle_websocket(websocket, task_id)


@router.post("/batch")
async def batch_process(keyword: str, max_results: int, background_tasks: BackgroundTasks):
    """批量处理视频"""
    if not video_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    return await video_processor.process_batch_videos(
        keyword,
        Platform.YOUTUBE,
        max_results,
        background_tasks
    )

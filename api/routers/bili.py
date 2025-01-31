import asyncio
import uuid

from fastapi import APIRouter, HTTPException, WebSocket, BackgroundTasks
from fastapi import WebSocketDisconnect

from db.models.subtitle import Platform
from services.bili2text.core.video_processor import VideoProcessor

router = APIRouter(prefix="/bili", tags=["bilibili"])

# 全局处理器实例
video_processor = None


def init_bili_processor(videoprocessor: VideoProcessor):
    """初始化Bilibili处理器"""
    global video_processor
    try:
        video_processor = videoprocessor
        return True
    except Exception as e:
        print(f"初始化Bilibili处理器失败: {str(e)}")
        return False


@router.post("/search")
async def search_videos(keyword: str, page: int = 1, page_size: int = 20):
    """搜索视频"""
    if not video_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    try:
        return await video_processor.downloader.search_videos(keyword, Platform.BILIBILI, page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/{bvid}")
async def get_video_text(bvid: str, background_tasks: BackgroundTasks):
    """获取视频字幕"""
    if not video_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    try:
        task_id = str(uuid.uuid4())
        print(f"创建任务: {task_id}")

        # 创建异步任务
        background_tasks.add_task(
            video_processor.process_single_video,
            bvid,
            Platform.BILIBILI,
            task_id
        )

        return {"task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_process(keyword: str, max_results: int, background_tasks: BackgroundTasks):
    """批量处理视频"""
    if not video_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    try:
        task_id = str(uuid.uuid4())
        print(f"创建批量任务: {task_id}")

        # 创建批量处理任务
        background_tasks.add_task(
            video_processor.process_batch_videos,
            keyword,
            Platform.BILIBILI,
            max_results,
            task_id
        )

        return {"task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket连接处理"""
    if not video_processor:
        await websocket.close(code=1000)
        return

    await websocket.accept()
    print(f"WebSocket连接已建立: {task_id}")

    try:
        while True:
            # 等待新的进度消息
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        print(f"WebSocket连接断开: {task_id}")
    except Exception as e:
        print(f"WebSocket错误: {str(e)}")
        await websocket.close(code=1000)

import asyncio
import uuid
from contextvars import copy_context
from typing import List
import time

from fastapi import APIRouter, HTTPException, WebSocket, BackgroundTasks
from fastapi import WebSocketDisconnect
from pydantic import BaseModel

from services.bili2text.core.youtube import YoutubeAPI
from services.bili2text.core.task_manager import TaskManager
from services.bili2text.core.task_status import TaskStatus
from services.bili2text.core.utils import current_task_id
from services.bili2text.main import Bili2Text

router = APIRouter(prefix="/youtube", tags=["youtube"])
youtube_api = YoutubeAPI()


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


class YoutubeProcessor:
    def __init__(self, bili2text: Bili2Text, youtube_api: YoutubeAPI, task_manager: TaskManager):
        self.bili2text = bili2text
        self.youtube_api = youtube_api
        self.task_manager = task_manager

    async def search_videos(self, keyword: str, page: int = 1, page_size: int = 20):
        try:
            return self.youtube_api.search_videos(keyword, page_size)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_video_text(self, video_id: str, background_tasks: BackgroundTasks):
        """异步处理视频文本获取请求"""
        if not self.task_manager:
            raise HTTPException(status_code=400, detail="服务未初始化")
        
        try:
            # 立即创建任务并返回task_id
            task_id = str(uuid.uuid4())
            self.task_manager.create_task(task_id)
            
            # 更新初始状态
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING.value,
                message="开始处理视频..."
            )
            
            # 使用asyncio.create_task创建异步任务
            asyncio.create_task(self._process_video_task(video_id, task_id))
            
            return {"task_id": task_id}
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def process_video(self, video_id: str) -> VideoResponse:
        try:
            result = self.bili2text.downloader.download_media(
                f"https://www.youtube.com/watch?v={video_id}"
            )

            return VideoResponse(
                id=video_id,
                title=self.youtube_api.get_video_info(video_id).get('title', ''),
                text=result['content'],
                type=result['type']
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def batch_process(self, keyword: str, max_results: int, background_tasks: BackgroundTasks):
        task_id = str(uuid.uuid4())
        self.task_manager.create_task(task_id)
        
        background_tasks.add_task(
            self._process_batch_task,
            keyword,
            max_results,
            task_id
        )
        
        return {"task_id": task_id}

    async def handle_websocket(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        print(f"WebSocket connection established for task: {task_id}")

        last_status = None
        try:
            while True:
                task_status = self.task_manager.get_task(task_id)

                if task_status is None:
                    await websocket.close(code=1000)
                    break

                if last_status != task_status:
                    await websocket.send_json(task_status)
                    last_status = task_status.copy()

                if task_status["status"] in ["completed", "failed"]:
                    await asyncio.sleep(1)
                    await websocket.close(code=1000)
                    break

                await asyncio.sleep(0.02)

        except WebSocketDisconnect:
            print(f"WebSocket disconnected: {task_id}")
        except Exception as e:
            print(f"WebSocket error: {str(e)}")
            await websocket.close(code=1000)
        finally:
            if task_id in self.task_manager.tasks:
                task_status = self.task_manager.get_task(task_id)
                if task_status and task_status["status"] in ["completed", "failed"]:
                    self.task_manager.remove_task(task_id)

    async def _process_video_task(self, video_id: str, task_id: str):
        """异步处理视频任务"""
        try:
            # 更新下载状态
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.DOWNLOADING.value,
                message="正在下载视频..."
            )
            
            # 使用asyncio.to_thread执行同步下载操作
            result = await asyncio.to_thread(
                self.bili2text.downloader.download_media,
                f"https://www.youtube.com/watch?v={video_id}",
                task_id
            )

            if result['type'] == 'subtitle':
                # 获取视频信息
                video_info = await asyncio.to_thread(
                    self.youtube_api.get_video_info,
                    video_id
                )
                
                self.task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED.value,
                    progress=100,
                    result={
                        "id": video_id,
                        "title": video_info.get('title', ''),
                        "text": result['content'],
                        "type": "subtitle"
                    }
                )
            elif result['type'] == 'audio':
                self.task_manager.update_task(
                    task_id,
                    status=TaskStatus.TRANSCRIBING.value,
                    progress=50,
                    message="正在转录音频..."
                )

                # 使用asyncio.to_thread执行转录操作
                text_path = await asyncio.to_thread(
                    self.bili2text.transcriber.transcribe_file,
                    result['content'],
                    task_id
                )

                with open(text_path, 'r', encoding='utf-8') as f:
                    text = f.read()

                # 获取视频信息
                video_info = await asyncio.to_thread(
                    self.youtube_api.get_video_info,
                    video_id
                )

                self.task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED.value,
                    progress=100,
                    result={
                        "id": video_id,
                        "title": video_info.get('title', ''),
                        "text": text,
                        "type": "audio"
                    }
                )

        except Exception as e:
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.FAILED.value,
                message=str(e)
            )

    async def _process_batch_task(self, keyword: str, max_results: int, task_id: str):
        try:
            videos = self.youtube_api.search_videos(keyword, max_results)
            results = []

            for i, video in enumerate(videos, 1):
                try:
                    result = await self.process_video(video['id'])
                    results.append(result)
                    self.task_manager.update_task(
                        task_id,
                        progress=(i / len(videos)) * 100,
                        message=f"处理进度: {i}/{len(videos)}"
                    )
                except Exception as e:
                    print(f"处理视频失败 {video['id']}: {str(e)}")

            self.task_manager.update_task(
                task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100,
                result={"results": [r.dict() for r in results]}
            )

        except Exception as e:
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.FAILED.value,
                message=str(e)
            )

# 创建路由处理器实例
youtube_processor = None

def init_youtube_processor(tm: TaskManager):
    """初始化YouTube处理器"""
    global youtube_processor
    try:
        youtube_api = YoutubeAPI()
        bili2text = Bili2Text(task_manager=tm)
        youtube_processor = YoutubeProcessor(bili2text, youtube_api, tm)
        return True
    except Exception as e:
        print(f"初始化YouTube处理器失败: {str(e)}")
        return False

# 路由定义
@router.post("/search")
async def search_videos(keyword: str, page: int = 1, page_size: int = 20):
    if not youtube_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    return await youtube_processor.search_videos(keyword, page, page_size)

@router.post("/video/{video_id}")
async def get_video_text(video_id: str, background_tasks: BackgroundTasks):
    if not youtube_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    res = await youtube_processor.get_video_text(video_id, background_tasks)
    return res

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    if not youtube_processor:
        await websocket.close(code=1000)
        return
    await youtube_processor.handle_websocket(websocket, task_id)

@router.post("/batch")
async def batch_process(
    keyword: str,
    max_results: int,
    background_tasks: BackgroundTasks
):
    if not youtube_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    return await youtube_processor.batch_process(keyword, max_results, background_tasks)

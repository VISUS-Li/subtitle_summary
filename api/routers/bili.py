import asyncio
import sys
import uuid
from contextvars import copy_context

from fastapi import APIRouter, HTTPException, WebSocket, BackgroundTasks
from fastapi import WebSocketDisconnect

from api.routers.base import VideoProcessor, VideoResponse
from db.models.subtitle import Platform
from services.bili2text.core.bilibili import BilibiliAPI
from services.bili2text.core.downloader import AudioDownloader
from services.bili2text.core.task_manager import TaskManager
from services.bili2text.core.transcriber import AudioTranscriber
from services.bili2text.core.utils import current_task_id

router = APIRouter(prefix="/bili", tags=["bilibili"])


class BiliProcessor(VideoProcessor):
    def __init__(self, downloader: AudioDownloader, transcriber: AudioTranscriber, bili_api: BilibiliAPI, task_manager: TaskManager):
        self.downloader = downloader
        self.transcriber = transcriber
        self.bili_api = bili_api
        self.task_manager = task_manager

    async def search_videos(self, keyword: str, page: int = 1, page_size: int = 20):
        try:
            return self.bili_api.search_videos(keyword, page_size)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_video_text(self, video_id: str, background_tasks: BackgroundTasks):
        try:
            task_id = str(uuid.uuid4())
            self.task_manager.create_task(task_id)

            background_tasks.add_task(
                self._process_video_task,
                video_id,
                task_id,
                is_youtube=False
            )

            return {"task_id": task_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def process_video(self, video_id: str) -> VideoResponse:
        try:
            result = self.downloader.download_media(
                f"https://www.bilibili.com/video/{video_id}"
            )

            return VideoResponse(
                id=video_id,
                title=self.bili_api.get_video_info(video_id).get('title', ''),
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

    async def _process_video_task(self, video_id: str, task_id: str, is_youtube: bool = False):
        token = None
        try:
            print(f"开始处理视频: {video_id}")
            result = self.downloader.download_media(
                f"https://www.bilibili.com/video/{video_id}",
                task_id
            )

            if result['type'] == 'subtitle':
                print("字幕下载完成")
                print(f"任务 {task_id} 完成:")
                print({
                    "id": video_id,
                    "text": result['content'],
                    "type": "subtitle"
                })
            elif result['type'] == 'audio':
                print("正在转录音频...")

                def transcribe_audio():
                    current_task_id.set(task_id)
                    return self.transcriber.transcribe_file(
                        result['content'],
                        result['video_id'],
                        Platform.BILIBILI,
                        task_id
                    )

                text = await asyncio.to_thread(copy_context().run, transcribe_audio)

                print("音频转录完成")
                print(f"任务 {task_id} 完成:")
                print({
                    "id": video_id,
                    "text": text,
                    "type": "audio"
                })

        except Exception as e:
            error_msg = f"处理视频失败 {video_id}: {str(e)}"
            print(error_msg, file=sys.stderr)
            print(f"任务 {task_id} 失败: {error_msg}")
            raise
        finally:
            if token is not None:
                current_task_id.reset(token)

    async def _process_batch_task(self, keyword: str, max_results: int, task_id: str):
        try:
            print(f"开始批量处理关键词: {keyword}, 最大结果数: {max_results}")
            videos = self.bili_api.search_videos(keyword, max_results)
            results = []

            for i, video in enumerate(videos, 1):
                try:
                    print(f"正在处理第 {i}/{len(videos)} 个视频: {video['bvid']}")
                    result = await self.process_video(video['bvid'])
                    results.append(result)
                    print(f"视频处理完成: {video['bvid']}")
                except Exception as e:
                    error_msg = f"处理视频失败 {video['bvid']}: {str(e)}"
                    print(error_msg, file=sys.stderr)

            print(f"批量处理完成，成功处理 {len(results)}/{len(videos)} 个视频")
            print(f"任务 {task_id} 完成:")
            print({
                "results": [r.dict() for r in results]
            })

        except Exception as e:
            error_msg = f"批量处理失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            print(f"任务 {task_id} 失败: {error_msg}")
            raise  # 重新抛出异常


# 创建路由处理器实例
bili_processor = None


def init_bili_processor(tm: TaskManager):
    """初始化B站处理器"""
    global bili_processor
    try:
        bili_api = BilibiliAPI()
        downloader = AudioDownloader(task_manager=tm)
        transcriber = AudioTranscriber(task_manager=tm)
        bili_processor = BiliProcessor(downloader, transcriber, bili_api, tm)
        return True
    except Exception as e:
        print(f"初始化B站处理器失败: {str(e)}")
        return False


# 路由定义
@router.post("/search")
async def search_videos(keyword: str, page: int = 1, page_size: int = 20):
    if not bili_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    return await bili_processor.search_videos(keyword, page, page_size)


@router.post("/video/{bvid}")
async def get_video_text(bvid: str, background_tasks: BackgroundTasks):
    if not bili_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    return await bili_processor.get_video_text(bvid, background_tasks)


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    if not bili_processor:
        await websocket.close(code=1000)
        return
    await bili_processor.handle_websocket(websocket, task_id)


@router.post("/batch")
async def batch_process(
        keyword: str,
        max_results: int,
        background_tasks: BackgroundTasks
):
    if not bili_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    return await bili_processor.batch_process(keyword, max_results, background_tasks)

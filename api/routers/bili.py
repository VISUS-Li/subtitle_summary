from fastapi import APIRouter, HTTPException, WebSocket, BackgroundTasks
from typing import List, Optional

from pydantic import BaseModel

from db.models import BiliConfig
from db.database import Database
from services.bili2text.config import get_config
from services.bili2text.main import Bili2Text
from services.bili2text.core.bilibili import BilibiliAPI
from services.bili2text.core.task_manager import TaskManager
from services.bili2text.core.task_status import TaskStatus
import asyncio
from fastapi import WebSocketDisconnect
import uuid
from services.bili2text.core.utils import current_task_id
import contextvars  # 引入contextvars
from contextvars import copy_context  # 修改这里，使用contextvars.copy_context

router = APIRouter(prefix="/bili", tags=["bilibili"])
db = Database()

# 全局变量
bili2text_instance = None
bili_api = None
task_manager = None  # 初始化为None，后续通过init_bili_service设置

def init_bili_service(tm: TaskManager, config=None):
    """初始化B站服务"""
    global bili2text_instance, bili_api, task_manager
    task_manager = tm  # 设置全局task_manager
    
    cookies = db.get_service_config("bilibili", "cookies")
    if cookies:
        try:
            bili_api = BilibiliAPI(**cookies)
            bili2text_instance = Bili2Text(task_manager=task_manager, config=config)  # 传入配置
            bili2text_instance.downloader.bili_api = bili_api
            return True
        except Exception as e:
            print(f"初始化B站服务失败: {str(e)}")
            return False
    return False

class VideoResponse(BaseModel):
    """视频响应模型"""
    bvid: str
    title: str
    text: str
    type: str  # 'subtitle' 或 'audio'

@router.post("/cookies")
async def set_cookies(cookies: BiliConfig):
    """设置B站cookies"""
    global bili2text_instance, bili_api
    try:
        bili_api = BilibiliAPI(
            sessdata=cookies.sessdata,
            bili_jct=cookies.bili_jct,
            buvid3=cookies.buvid3
        )
        # 获取最新配置
        config = get_config()
        bili2text_instance = Bili2Text(task_manager=task_manager, config=config)
        bili2text_instance.downloader.bili_api = bili_api
        
        # 存储cookies
        db.set_service_config("bilibili", "cookies", cookies.dict())
        return {"message": "Cookies设置成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/cookies")
async def get_cookies() -> Optional[BiliConfig]:
    """获取已存储的cookies"""
    cookies = db.get_service_config("bilibili", "cookies")
    if cookies:
        return BiliConfig(**cookies)
    raise HTTPException(status_code=404, detail="未找到存储的cookies")

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    print(f"WebSocket connection established for task: {task_id}")
    
    last_status = None  # 用于跟踪上一次的状态
    try:
        while True:
            task_status = task_manager.get_task(task_id)
            
            if task_status is None:
                print(f"Task {task_id} not found")
                await websocket.close(code=1000)
                break
            
            # 只在状态不同时才发送消息
            if last_status != task_status:
                await websocket.send_json(task_status)
                last_status = task_status.copy()  # 深拷贝当前状态用于下次比较
            
            if task_status["status"] in ["completed", "failed"]:
                print(f"Task {task_id} finished with status: {task_status['status']}")
                await asyncio.sleep(1)
                await websocket.close(code=1000)
                break
            
            await asyncio.sleep(0.02)
            
    except WebSocketDisconnect:
        print(f"WebSocket connection disconnected: {task_id}")
    except Exception as e:
        print(f"WebSocket error for task {task_id}: {str(e)}")
        await websocket.close(code=1000)
    finally:
        if task_id in task_manager.tasks:
            task_status = task_manager.get_task(task_id)
            if task_status and task_status["status"] in ["completed", "failed"]:
                task_manager.remove_task(task_id)

@router.get("/video/{bvid}")
async def get_video_text(bvid: str, background_tasks: BackgroundTasks):
    """获取视频字幕，立即返回task_id，后台处理任务"""
    if not bili2text_instance:
        raise HTTPException(status_code=400, detail="请先设置cookies")
    
    try:
        task_id = str(uuid.uuid4())
        task_manager.create_task(task_id)
        
        # 获取最新配置
        config = get_config()
        # 更新bili2text实例的配置
        bili2text_instance.update_config(config)
        
        # 确保bili2text_instance的组件都有task_manager
        bili2text_instance.downloader.task_manager = task_manager
        bili2text_instance.transcriber.task_manager = task_manager
        
        background_tasks.add_task(
            process_video_task,
            bvid,
            task_id,
            bili2text_instance,
            task_manager
        )
        
        return {"task_id": task_id}
        
    except Exception as e:
        print(f"创建任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_video_task(bvid: str, task_id: str, bili2text: Bili2Text, task_manager: TaskManager):
    """后台处理视频任务"""
    # 保存当前的token，以便在finally中恢复
    token = None
    try:
        url = f"https://www.bilibili.com/video/{bvid}"
        
        # 设置当前task_id到ContextVar
        token = current_task_id.set(task_id)
        
        # 更新任务状态为开始处理
        task_manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING.value,
            progress=0,
            message="开始处理视频..."
        )
        
        # 定义在后台线程中运行的函数
        def download_and_process():
            # 设置当前task_id
            current_task_id.set(task_id)
            return bili2text.downloader.download_from_url(url, task_id)
        
        # 使用contextvars.copy_context确保ContextVar被复制到新的线程
        result = await asyncio.to_thread(copy_context().run, download_and_process)
        
        if result['type'] == 'subtitle':
            # 如果是字幕，直接返回结果
            task_manager.update_task(
                task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100,
                message="字幕获取成功",
                result={
                    "bvid": bvid,
                    "text": result['subtitle_text'],
                    "type": "subtitle"
                }
            )
        elif result['type'] == 'audio':
            # 如果是音频，需要转录
            task_manager.update_task(
                task_id,
                status=TaskStatus.TRANSCRIBING.value,
                progress=50,
                message="正在转录音频..."
            )
            
            # 定义在后台线程中运行的转录函数
            def transcribe_audio():
                current_task_id.set(task_id)
                return bili2text.transcriber.transcribe_file(
                    result['audio_path'],
                    task_id
                )
            
            # 使用contextvars.copy_context确保ContextVar被复制到新的线程
            text_path = await asyncio.to_thread(copy_context().run, transcribe_audio)
            
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read()
                
            task_manager.update_task(
                task_id,
                status=TaskStatus.COMPLETED.value,
                progress=100,
                message="转录完成",
                result={
                    "bvid": bvid,
                    "text": text,
                    "type": "audio"
                }
            )
        else:
            raise Exception("无法获取视频内容")
        
    except Exception as e:
        print(f"处理视频失败: {str(e)}")
        task_manager.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            message=str(e)
        )
    finally:
        # 只有在设置了token的情况下才重置
        if token is not None:
            current_task_id.reset(token)

@router.get("/search")
async def search_videos(keyword: str, page: int = 1, page_size: int = 20):
    """搜索视频"""
    if not bili_api:
        raise HTTPException(status_code=400, detail="请先设置cookies")
    
    try:
        videos = bili_api.search_videos(keyword, page_size)
        return videos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch")
async def batch_process(keyword: str, max_results: int = 5) -> List[VideoResponse]:
    """批量处理视频"""
    if not bili2text_instance:
        raise HTTPException(status_code=400, detail="请先设置cookies")
    
    try:
        results = []
        videos = bili_api.search_videos(keyword, max_results)
        
        for video in videos:
            bvid = video['bvid']
            url = f"https://www.bilibili.com/video/{bvid}"
            result = bili2text_instance.downloader.download_from_url(url)
            
            if result['type'] == 'subtitle':
                text = result['subtitle_text']
            elif result['type'] == 'audio':
                text_path = bili2text_instance.transcriber.transcribe_file(result['audio_path'])
                with open(text_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                continue
                
            results.append(VideoResponse(
                bvid=bvid,
                title=video['title'],
                text=text,
                type=result['type']
            ))
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ... 其他B站相关API端点 ... 
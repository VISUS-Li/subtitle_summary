from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse
from db.models.subtitle import Platform
from services.bili2text.core.video_processor import VideoProcessor
from enum import Enum
import asyncio
import uuid
import sys

router = APIRouter(prefix="/video", tags=["video"])

# 全局处理器实例
video_processor = None

# 添加一个新的枚举类来定义平台选择
class PlatformChoice(str, Enum):
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"
    ALL = "all"

# 添加一个新的请求模型
class BatchProcessRequest(BaseModel):
    topic: str
    keyword: str
    max_results: int = 200
    platform_choice: PlatformChoice


def init_video_processor(processor: VideoProcessor):
    """初始化视频处理器"""
    global video_processor
    try:
        video_processor = processor
        return True
    except Exception as e:
        print(f"初始化视频处理器失败: {str(e)}")
        return False


class VideoUrlRequest(BaseModel):
    """视频URL请求模型"""
    url: HttpUrl
    language: Optional[str] = "zh"
    topic: str  # 新增必填字段


class VideoResponse(BaseModel):
    """视频响应模型"""
    video_id: str
    platform: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    summary: Optional[str] = None


def parse_video_url(url: str) -> tuple[str, Platform]:
    """解析视频URL，获取视频ID和平台信息
    
    Args:
        url: 视频URL
        
    Returns:
        tuple: (视频ID, 平台)
        
    Raises:
        ValueError: URL格式无效
    """
    parsed = urlparse(str(url))
    
    # 处理B站链接
    if 'bilibili.com' in parsed.netloc:
        # 提取BV号
        path_parts = parsed.path.split('/')
        for part in path_parts:
            if part.startswith('BV'):
                return part, Platform.BILIBILI
        raise ValueError("无效的B站视频链接")
    
    # 处理YouTube链接
    elif 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
        if 'youtube.com' in parsed.netloc:
            # 从查询参数中获取视频ID
            from urllib.parse import parse_qs
            query = parse_qs(parsed.query)
            video_id = query.get('v', [None])[0]
            if not video_id:
                raise ValueError("无效的YouTube视频链接")
        else:
            # 从youtu.be短链接中获取视频ID
            video_id = parsed.path.lstrip('/')
            
        return video_id, Platform.YOUTUBE
        
    else:
        raise ValueError("不支持的视频平台")


@router.post("/process", response_model=VideoResponse)
async def process_video(request: VideoUrlRequest):
    """处理单个视频链接
    
    Args:
        request: 包含视频URL的请求
        
    Returns:
        VideoResponse: 处理结果
    """
    if not video_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
        
    try:
        # 1. 解析视频URL
        video_id, platform = parse_video_url(str(request.url))
        print(f"开始处理视频: {platform.value} - {video_id}")
        
        # 2. 处理视频获取字幕
        result, summary_task = await video_processor.process_single_video(
            topic=request.topic,  # 添加topic参数
            video_id=video_id,
            platform=platform
        )
        
        # 3. 等待总结任务完成
        if summary_task:
            try:
                print("等待字幕总结任务完成...")
                await summary_task
                print("字幕总结任务已完成")
            except Exception as e:
                print(f"字幕总结任务失败: {str(e)}")
        
        # 4. 获取视频信息和总结
        video_info = video_processor.subtitle_manager.get_video_info(platform, video_id)
        subtitle = video_processor.subtitle_manager.get_subtitle(video_id)
        
        if subtitle:
            summary = video_processor.subtitle_manager.get_subtitle_summary(subtitle['id'])
        else:
            summary = None
            
        # 5. 构造响应
        return VideoResponse(
            video_id=video_id,
            platform=platform.value,
            title=video_info.get('title') if video_info else None,
            subtitle=subtitle.get('content') if subtitle else None,
            summary=summary.get('content') if summary else None
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_process_videos(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks
):
    """批量处理多平台视频
    
    Args:
        request: 包含处理参数的请求对象
        background_tasks: FastAPI后台任务对象
        
    Returns:
        Dict: 包含任务ID的响应
    """
    if not video_processor:
        raise HTTPException(status_code=400, detail="服务未初始化")
    
    try:
        task_id = str(uuid.uuid4())
        print(f"创建批量处理任务: {task_id}")

        async def process_platform(platform: Platform):
            try:
                await video_processor.process_batch_videos(
                    request.topic,
                    request.keyword,
                    platform,
                    request.max_results
                )
            except Exception as e:
                print(f"{platform.value} 平台处理失败: {str(e)}")
                raise

        # 根据用户选择的平台执行相应的处理
        if request.platform_choice == PlatformChoice.ALL:
            # 同时处理两个平台
            background_tasks.add_task(
                lambda: asyncio.gather(
                    process_platform(Platform.BILIBILI),
                    process_platform(Platform.YOUTUBE)
                )
            )
        elif request.platform_choice == PlatformChoice.BILIBILI:
            # 只处理B站
            background_tasks.add_task(
                process_platform,
                Platform.BILIBILI
            )
        else:
            # 只处理YouTube
            background_tasks.add_task(
                process_platform,
                Platform.YOUTUBE
            )

        return {
            "task_id": task_id,
            "message": f"已开始{request.platform_choice.value}平台的批量处理任务"
        }

    except Exception as e:
        error_msg = f"创建批量处理任务失败: {str(e)}"
        print(error_msg, file=sys.stderr)
        raise HTTPException(status_code=500, detail=error_msg) 
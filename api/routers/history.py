from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, distinct, func
from db.init.base import get_db
from db.models.subtitle import Video, Subtitle, SubtitleSummary, GeneratedScript, Platform, TaskStatus
from enum import Enum

router = APIRouter(prefix="/history", tags=["history"])

# 枚举类定义排序方式
class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

# 枚举类定义排序字段
class SortField(str, Enum):
    CREATE_TIME = "create_time"
    UPDATE_TIME = "update_time"
    TITLE = "title"
    AUTHOR = "author"
    VIEW_COUNT = "view_count"

# 基础响应模型
class PaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    has_more: bool

# 先定义基础的视频信息模型（不包含关联字段）
class VideoInfoBase(BaseModel):
    id: str
    platform: str
    platform_vid: str
    title: Optional[str] = None
    author: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    description: Optional[str] = None
    create_time: datetime
    update_time: datetime
    search_keyword: Optional[str] = None
    search_rank: Optional[int] = None

# 字幕信息响应模型
class SubtitleInfo(BaseModel):
    id: int
    video_id: str
    content: str
    language: str
    create_time: datetime
    video: Optional[VideoInfoBase] = None

# 字幕总结响应模型
class SummaryInfo(BaseModel):
    id: int
    subtitle_id: int
    content: str
    create_time: datetime
    status: str
    score: Optional[float]
    video: Optional[VideoInfoBase] = None
    subtitle: Optional[SubtitleInfo] = None

# 完整的视频信息模型（包含关联字段）
class VideoInfo(VideoInfoBase):
    subtitles: Optional[List[SubtitleInfo]] = None
    summaries: Optional[List[SummaryInfo]] = None

# 脚本信息响应模型
class ScriptInfo(BaseModel):
    id: int
    topic: str
    platform: str
    content: str
    video_count: int
    create_time: datetime
    update_time: datetime

# 各种历史记录响应模型
class VideoHistoryResponse(PaginationResponse):
    items: List[VideoInfo]

class SubtitleHistoryResponse(PaginationResponse):
    items: List[SubtitleInfo]

class SummaryHistoryResponse(PaginationResponse):
    items: List[SummaryInfo]

class ScriptHistoryResponse(PaginationResponse):
    items: List[ScriptInfo]

# 搜索结果响应模型
class SearchResponse(BaseModel):
    videos: List[VideoInfo]
    subtitles: List[SubtitleInfo]
    summaries: List[SummaryInfo]
    scripts: List[ScriptInfo]

# 关键词响应模型
class KeywordResponse(BaseModel):
    search_keywords: List[str]
    topics: List[str]

@router.get("/videos", response_model=VideoHistoryResponse)
async def get_video_history(
    keyword: Optional[str] = None,
    topic: Optional[str] = None,
    platform: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = Query(1, gt=0),
    page_size: int = Query(10, gt=0),
    sort_field: SortField = SortField.CREATE_TIME,
    sort_order: SortOrder = SortOrder.DESC
):
    """获取视频历史记录"""
    try:
        with get_db() as db:
            # 首先查找包含该主题的脚本
            video_ids = []
            if topic:
                scripts = db.query(GeneratedScript).filter(
                    GeneratedScript.topic == topic
                ).all()
                # 收集所有相关的视频ID
                for script in scripts:
                    if script.video_ids:  # 确保video_ids不为空
                        video_ids.extend(script.video_ids)
                video_ids = list(set(video_ids))  # 去重
            
            # 构建基础查询
            query = db.query(Video)
            
            # 如果指定了主题，只查询相关视频
            if topic and video_ids:
                query = query.filter(Video.id.in_(video_ids))
            elif topic and not video_ids:
                # 如果指定了主题但没找到相关视频，返回空结果
                return VideoHistoryResponse(
                    total=0,
                    page=page,
                    page_size=page_size,
                    has_more=False,
                    items=[]
                )
            
            # 关键词搜索
            if keyword:
                query = query.filter(
                    or_(
                        Video.title.ilike(f"%{keyword}%"),
                        Video.author.ilike(f"%{keyword}%"),
                        Video.description.ilike(f"%{keyword}%"),
                        Video.search_keyword.ilike(f"%{keyword}%")
                    )
                )
            
            # 平台筛选
            if platform and platform.strip():
                query = query.filter(Video.platform == Platform(platform))
                
            # 时间范围筛选
            if start_time:
                query = query.filter(Video.create_time >= start_time)
            if end_time:
                query = query.filter(Video.create_time <= end_time)
                
            # 获取总数
            total = query.count()
            
            # 排序
            sort_column = getattr(Video, sort_field.value)
            if sort_order == SortOrder.DESC:
                sort_column = sort_column.desc()
            query = query.order_by(sort_column)
            
            # 分页
            videos = query.offset((page - 1) * page_size).limit(page_size).all()
            
            return VideoHistoryResponse(
                total=total,
                page=page,
                page_size=page_size,
                has_more=total > page * page_size,
                items=[
                    VideoInfo(
                        id=video.id,
                        platform=video.platform.value,
                        platform_vid=video.platform_vid,
                        title=video.title,
                        author=video.author,
                        duration=video.duration,
                        view_count=video.view_count,
                        tags=video.tags,
                        keywords=video.keywords,
                        description=video.description,
                        create_time=video.create_time,
                        update_time=video.update_time,
                        search_keyword=video.search_keyword,
                        search_rank=video.search_rank
                    )
                    for video in videos
                ]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subtitles", response_model=SubtitleHistoryResponse)
async def get_subtitle_history(
    keyword: Optional[str] = None,
    platform: Optional[Platform] = None,
    language: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    sort_order: SortOrder = SortOrder.DESC,
    page: int = Query(1, gt=0),
    page_size: int = Query(20, gt=0, le=100)
):
    """获取字幕历史记录"""
    try:
        with get_db() as db:
            query = db.query(Subtitle).join(Video)
            
            # 添加筛选条件
            if keyword:
                query = query.filter(
                    or_(
                        Subtitle.content.ilike(f"%{keyword}%"),
                        Video.title.ilike(f"%{keyword}%")
                    )
                )
            
            if platform:
                query = query.filter(Video.platform == platform)
                
            if language:
                query = query.filter(Subtitle.language == language)
                
            if start_time:
                query = query.filter(Subtitle.create_time >= start_time)
                
            if end_time:
                query = query.filter(Subtitle.create_time <= end_time)
            
            # 添加排序
            if sort_order == SortOrder.DESC:
                query = query.order_by(Subtitle.create_time.desc())
            else:
                query = query.order_by(Subtitle.create_time.asc())
            
            # 计算总数
            total = query.count()
            
            # 分页
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # 获取结果
            subtitles = query.all()
            
            return SubtitleHistoryResponse(
                total=total,
                page=page,
                page_size=page_size,
                has_more=total > page * page_size,
                items=[
                    SubtitleInfo(
                        id=subtitle.id,
                        video_id=subtitle.video_id,
                        content=subtitle.content,
                        language=subtitle.language,
                        create_time=subtitle.create_time,
                        video=VideoInfo(
                            id=subtitle.video.id,
                            platform=subtitle.video.platform.value,
                            platform_vid=subtitle.video.platform_vid,
                            title=subtitle.video.title,
                            author=subtitle.video.author,
                            duration=subtitle.video.duration,
                            view_count=subtitle.video.view_count,
                            tags=subtitle.video.tags,
                            keywords=subtitle.video.keywords,
                            description=subtitle.video.description,
                            create_time=subtitle.video.create_time,
                            update_time=subtitle.video.update_time,
                            search_keyword=subtitle.video.search_keyword,
                            search_rank=subtitle.video.search_rank
                        )
                    )
                    for subtitle in subtitles
                ]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summaries", response_model=SummaryHistoryResponse)
async def get_summary_history(
    keyword: Optional[str] = None,
    platform: Optional[Platform] = None,
    status: Optional[TaskStatus] = None,
    min_score: Optional[float] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    sort_order: SortOrder = SortOrder.DESC,
    page: int = Query(1, gt=0),
    page_size: int = Query(20, gt=0, le=100)
):
    """获取字幕总结历史记录"""
    try:
        with get_db() as db:
            query = db.query(SubtitleSummary).join(Subtitle).join(Video)
            
            # 添加筛选条件
            if keyword:
                query = query.filter(
                    or_(
                        SubtitleSummary.content.ilike(f"%{keyword}%"),
                        Video.title.ilike(f"%{keyword}%")
                    )
                )
            
            if platform:
                query = query.filter(Video.platform == platform)
                
            if status:
                query = query.filter(SubtitleSummary.status == status)
                
            if min_score is not None:
                query = query.filter(SubtitleSummary.score >= min_score)
                
            if start_time:
                query = query.filter(SubtitleSummary.create_time >= start_time)
                
            if end_time:
                query = query.filter(SubtitleSummary.create_time <= end_time)
            
            # 添加排序
            if sort_order == SortOrder.DESC:
                query = query.order_by(SubtitleSummary.create_time.desc())
            else:
                query = query.order_by(SubtitleSummary.create_time.asc())
            
            # 计算总数
            total = query.count()
            
            # 分页
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # 获取结果
            summaries = query.all()
            
            return SummaryHistoryResponse(
                total=total,
                page=page,
                page_size=page_size,
                has_more=total > page * page_size,
                items=[
                    SummaryInfo(
                        id=summary.id,
                        subtitle_id=summary.subtitle_id,
                        content=summary.content,
                        create_time=summary.create_time,
                        status=summary.status.value,
                        score=summary.score,
                        subtitle=SubtitleInfo(
                            id=summary.subtitle.id,
                            video_id=summary.subtitle.video_id,
                            content=summary.subtitle.content,
                            language=summary.subtitle.language,
                            create_time=summary.subtitle.create_time,
                            video=VideoInfo(
                                id=summary.subtitle.video.id,
                                platform=summary.subtitle.video.platform.value,
                                platform_vid=summary.subtitle.video.platform_vid,
                                title=summary.subtitle.video.title,
                                author=summary.subtitle.video.author,
                                duration=summary.subtitle.video.duration,
                                view_count=summary.subtitle.video.view_count,
                                tags=summary.subtitle.video.tags,
                                keywords=summary.subtitle.video.keywords,
                                description=summary.subtitle.video.description,
                                create_time=summary.subtitle.video.create_time,
                                update_time=summary.subtitle.video.update_time,
                                search_keyword=summary.subtitle.video.search_keyword,
                                search_rank=summary.subtitle.video.search_rank
                            )
                        ),
                        video=VideoInfo(
                            id=summary.subtitle.video.id,
                            platform=summary.subtitle.video.platform.value,
                            platform_vid=summary.subtitle.video.platform_vid,
                            title=summary.subtitle.video.title,
                            author=summary.subtitle.video.author,
                            duration=summary.subtitle.video.duration,
                            view_count=summary.subtitle.video.view_count,
                            tags=summary.subtitle.video.tags,
                            keywords=summary.subtitle.video.keywords,
                            description=summary.subtitle.video.description,
                            create_time=summary.subtitle.video.create_time,
                            update_time=summary.subtitle.video.update_time,
                            search_keyword=summary.subtitle.video.search_keyword,
                            search_rank=summary.subtitle.video.search_rank
                        )
                    )
                    for summary in summaries
                ]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scripts", response_model=ScriptHistoryResponse)
async def get_script_history(
    keyword: Optional[str] = None,
    platform: Optional[Platform] = None,
    topic: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    sort_order: SortOrder = SortOrder.DESC,
    page: int = Query(1, gt=0),
    page_size: int = Query(20, gt=0, le=100)
):
    """获取生成脚本历史记录"""
    try:
        with get_db() as db:
            query = db.query(GeneratedScript)
            
            # 添加筛选条件
            if keyword:
                query = query.filter(
                    or_(
                        GeneratedScript.content.ilike(f"%{keyword}%"),
                        GeneratedScript.topic.ilike(f"%{keyword}%")
                    )
                )
            
            if platform:
                query = query.filter(GeneratedScript.platform == platform)
                
            if topic:
                query = query.filter(GeneratedScript.topic == topic)
                
            if start_time:
                query = query.filter(GeneratedScript.create_time >= start_time)
                
            if end_time:
                query = query.filter(GeneratedScript.create_time <= end_time)
            
            # 添加排序
            if sort_order == SortOrder.DESC:
                query = query.order_by(GeneratedScript.create_time.desc())
            else:
                query = query.order_by(GeneratedScript.create_time.asc())
            
            # 计算总数
            total = query.count()
            
            # 分页
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # 获取结果
            scripts = query.all()
            
            return ScriptHistoryResponse(
                total=total,
                page=page,
                page_size=page_size,
                has_more=total > page * page_size,
                items=[
                    ScriptInfo(
                        id=script.id,
                        topic=script.topic,
                        platform=script.platform.value,
                        content=script.content,
                        video_count=script.video_count,
                        create_time=script.create_time,
                        update_time=script.update_time
                    )
                    for script in scripts
                ]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=SearchResponse)
async def search_all(
    keyword: str,
    platform: Optional[Platform] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(10, gt=0, le=50)
):
    """全局搜索接口"""
    try:
        with get_db() as db:
            # 搜索视频
            video_query = db.query(Video).filter(
                or_(
                    Video.title.ilike(f"%{keyword}%"),
                    Video.author.ilike(f"%{keyword}%"),
                    Video.description.ilike(f"%{keyword}%"),
                    Video.search_keyword.ilike(f"%{keyword}%")
                )
            )
            
            # 搜索字幕
            subtitle_query = db.query(Subtitle).join(Video).filter(
                or_(
                    Subtitle.content.ilike(f"%{keyword}%"),
                    Video.title.ilike(f"%{keyword}%")
                )
            )
            
            # 搜索总结
            summary_query = db.query(SubtitleSummary).join(Subtitle).join(Video).filter(
                or_(
                    SubtitleSummary.content.ilike(f"%{keyword}%"),
                    Video.title.ilike(f"%{keyword}%")
                )
            )
            
            # 搜索脚本
            script_query = db.query(GeneratedScript).filter(
                or_(
                    GeneratedScript.content.ilike(f"%{keyword}%"),
                    GeneratedScript.topic.ilike(f"%{keyword}%")
                )
            )
            
            # 添加平台筛选
            if platform:
                video_query = video_query.filter(Video.platform == platform)
                subtitle_query = subtitle_query.filter(Video.platform == platform)
                summary_query = summary_query.filter(Video.platform == platform)
                script_query = script_query.filter(GeneratedScript.platform == platform)
            
            # 添加时间筛选
            if start_time:
                video_query = video_query.filter(Video.create_time >= start_time)
                subtitle_query = subtitle_query.filter(Subtitle.create_time >= start_time)
                summary_query = summary_query.filter(SubtitleSummary.create_time >= start_time)
                script_query = script_query.filter(GeneratedScript.create_time >= start_time)
            
            if end_time:
                video_query = video_query.filter(Video.create_time <= end_time)
                subtitle_query = subtitle_query.filter(Subtitle.create_time <= end_time)
                summary_query = summary_query.filter(SubtitleSummary.create_time <= end_time)
                script_query = script_query.filter(GeneratedScript.create_time <= end_time)
            
            # 获取结果
            videos = video_query.limit(limit).all()
            subtitles = subtitle_query.limit(limit).all()
            summaries = summary_query.limit(limit).all()
            scripts = script_query.limit(limit).all()
            
            return SearchResponse(
                videos=[
                    VideoInfo(
                        id=video.id,
                        platform=video.platform.value,
                        platform_vid=video.platform_vid,
                        title=video.title,
                        author=video.author,
                        duration=video.duration,
                        view_count=video.view_count,
                        tags=video.tags,
                        keywords=video.keywords,
                        description=video.description,
                        create_time=video.create_time,
                        update_time=video.update_time,
                        search_keyword=video.search_keyword,
                        search_rank=video.search_rank
                    )
                    for video in videos
                ],
                subtitles=[
                    SubtitleInfo(
                        id=subtitle.id,
                        video_id=subtitle.video_id,
                        content=subtitle.content,
                        language=subtitle.language,
                        create_time=subtitle.create_time,
                        video=VideoInfo(
                            id=subtitle.video.id,
                            platform=subtitle.video.platform.value,
                            platform_vid=subtitle.video.platform_vid,
                            title=subtitle.video.title,
                            author=subtitle.video.author,
                            duration=subtitle.video.duration,
                            view_count=subtitle.video.view_count,
                            tags=subtitle.video.tags,
                            keywords=subtitle.video.keywords,
                            description=subtitle.video.description,
                            create_time=subtitle.video.create_time,
                            update_time=subtitle.video.update_time,
                            search_keyword=subtitle.video.search_keyword,
                            search_rank=subtitle.video.search_rank
                        )
                    )
                    for subtitle in subtitles
                ],
                summaries=[
                    SummaryInfo(
                        id=summary.id,
                        subtitle_id=summary.subtitle_id,
                        content=summary.content,
                        create_time=summary.create_time,
                        status=summary.status.value,
                        score=summary.score,
                        subtitle=SubtitleInfo(
                            id=summary.subtitle.id,
                            video_id=summary.subtitle.video_id,
                            content=summary.subtitle.content,
                            language=summary.subtitle.language,
                            create_time=summary.subtitle.create_time,
                            video=VideoInfo(
                                id=summary.subtitle.video.id,
                                platform=summary.subtitle.video.platform.value,
                                platform_vid=summary.subtitle.video.platform_vid,
                                title=summary.subtitle.video.title,
                                author=summary.subtitle.video.author,
                                duration=summary.subtitle.video.duration,
                                view_count=summary.subtitle.video.view_count,
                                tags=summary.subtitle.video.tags,
                                keywords=summary.subtitle.video.keywords,
                                description=summary.subtitle.video.description,
                                create_time=summary.subtitle.video.create_time,
                                update_time=summary.subtitle.video.update_time,
                                search_keyword=summary.subtitle.video.search_keyword,
                                search_rank=summary.subtitle.video.search_rank
                            )
                        ),
                        video=VideoInfo(
                            id=summary.subtitle.video.id,
                            platform=summary.subtitle.video.platform.value,
                            platform_vid=summary.subtitle.video.platform_vid,
                            title=summary.subtitle.video.title,
                            author=summary.subtitle.video.author,
                            duration=summary.subtitle.video.duration,
                            view_count=summary.subtitle.video.view_count,
                            tags=summary.subtitle.video.tags,
                            keywords=summary.subtitle.video.keywords,
                            description=summary.subtitle.video.description,
                            create_time=summary.subtitle.video.create_time,
                            update_time=summary.subtitle.video.update_time,
                            search_keyword=summary.subtitle.video.search_keyword,
                            search_rank=summary.subtitle.video.search_rank
                        )
                    )
                    for summary in summaries
                ],
                scripts=[
                    ScriptInfo(
                        id=script.id,
                        topic=script.topic,
                        platform=script.platform.value,
                        content=script.content,
                        video_count=script.video_count,
                        create_time=script.create_time,
                        update_time=script.update_time
                    )
                    for script in scripts
                ]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/keywords", response_model=KeywordResponse)
async def get_keywords():
    """获取所有已有的关键词列表
    
    Returns:
        KeywordResponse: 包含搜索关键词和主题的响应
    """
    try:
        with get_db() as db:
            # 获取视频的搜索关键词（去重）
            search_keywords = db.query(distinct(Video.search_keyword))\
                .filter(Video.search_keyword.isnot(None))\
                .all()
            search_keywords = [kw[0] for kw in search_keywords if kw[0]]

            # 获取脚本的主题（去重）
            topics = db.query(distinct(GeneratedScript.topic))\
                .filter(GeneratedScript.topic.isnot(None))\
                .all()
            topics = [topic[0] for topic in topics if topic[0]]

            return KeywordResponse(
                search_keywords=search_keywords,
                topics=topics
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/videos/{video_id}", response_model=VideoInfo)
async def get_video_detail(video_id: str):
    """获取视频详情，包括关联的字幕和总结信息"""
    try:
        with get_db() as db:
            video = db.query(Video)\
                .filter(Video.id == video_id)\
                .first()
            
            if not video:
                raise HTTPException(status_code=404, detail="视频不存在")
            
            # 获取关联的字幕
            subtitles = db.query(Subtitle)\
                .filter(Subtitle.video_id == video_id)\
                .all()
                
            # 获取关联的总结
            summaries = db.query(SubtitleSummary)\
                .join(Subtitle)\
                .filter(Subtitle.video_id == video_id)\
                .all()
                
            return VideoInfo(
                id=video.id,
                platform=video.platform.value,
                platform_vid=video.platform_vid,
                title=video.title,
                author=video.author,
                duration=video.duration,
                view_count=video.view_count,
                tags=video.tags,
                keywords=video.keywords,
                description=video.description,
                create_time=video.create_time,
                update_time=video.update_time,
                search_keyword=video.search_keyword,
                search_rank=video.search_rank,
                subtitles=[
                    SubtitleInfo(
                        id=subtitle.id,
                        video_id=subtitle.video_id,
                        content=subtitle.content,
                        language=subtitle.language,
                        create_time=subtitle.create_time,
                        video=None  # 避免循环引用
                    )
                    for subtitle in subtitles
                ],
                summaries=[
                    SummaryInfo(
                        id=summary.id,
                        subtitle_id=summary.subtitle_id,
                        content=summary.content,
                        create_time=summary.create_time,
                        status=summary.status.value,
                        score=summary.score,
                        video=None,  # 避免循环引用
                        subtitle=None  # 避免循环引用
                    )
                    for summary in summaries
                ]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from db.init.base import Base
import enum
import uuid


class Platform(enum.Enum):
    """视频平台"""
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"


class SubtitleSource(enum.Enum):
    """字幕来源类型"""
    OFFICIAL = "official"  # 官方外挂字幕
    WHISPER = "whisper"  # Whisper生成字幕


class Video(Base):
    """视频信息表"""
    __tablename__ = "videos"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))  # 内部ID
    platform = Column(Enum(Platform), nullable=False)

    # 平台特定信息
    platform_vid = Column(String(64))  # 平台视频ID (YouTube vid 或 B站 bvid)

    # B站特定信息
    bilibili_aid = Column(String(32))  # B站 aid
    bilibili_cid = Column(String(32))  # B站 cid

    # YouTube特定信息
    youtube_channel_id = Column(String(64))  # YouTube频道ID
    youtube_playlist_id = Column(String(64))  # YouTube播放列表ID

    # 通用信息
    title = Column(String(500))
    author = Column(String(255))
    duration = Column(Integer)  # 视频时长(秒)
    view_count = Column(Integer)
    tags = Column(JSON)  # 视频标签
    keywords = Column(JSON)  # 视频关键词
    description = Column(Text)
    audio_path = Column(String(500))  # 音频文件路径
    extra_info = Column(JSON)  # 其他平台特定信息

    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 新增字段
    source_type = Column(String(20), nullable=True)  # 'search' 或 'direct'
    search_keyword = Column(String(255), nullable=True)  # 搜索关键词
    search_rank = Column(Integer, nullable=True)  # 搜索结果中的排名

    # 关联字幕
    subtitles = relationship("Subtitle", back_populates="video")


class TaskStatus(enum.Enum):
    """任务状态"""
    PENDING = "pending"    # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 完成
    FAILED = "failed"      # 失败


class SubtitleSummary(Base):
    """字幕总结表"""
    __tablename__ = "subtitle_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subtitle_id = Column(Integer, ForeignKey("subtitles.id"), nullable=False)
    content = Column(Text(length=4294967295))  # 总结内容
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联字幕
    subtitle = relationship("Subtitle", back_populates="summary")

    # 添加新字段
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    error_message = Column(Text, nullable=True)  # 错误信息
    retry_count = Column(Integer, default=0)     # 重试次数
    workflow_id = Column(String(64), nullable=True)  # Coze工作流ID
    last_retry_time = Column(DateTime, nullable=True)  # 上次重试时间


class Subtitle(Base):
    """字幕信息表"""
    __tablename__ = "subtitles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(64), ForeignKey("videos.id"), nullable=False)
    platform_vid = Column(String(64), nullable=False)
    platform = Column(Enum(Platform), nullable=False)
    source = Column(Enum(SubtitleSource), nullable=False)
    # 使用 LONGTEXT 存储纯文本内容
    content = Column(Text(length=4294967295), nullable=False)
    # 使用 JSON 类型存储带时间戳的内容，MySQL会自动处理序列化
    timed_content = Column(JSON, nullable=True)
    language = Column(String(10))
    model_name = Column(String(50))
    create_time = Column(DateTime, default=datetime.utcnow)

    # 关联视频
    video = relationship("Video", back_populates="subtitles")

    # 新增字段
    summary = relationship("SubtitleSummary", back_populates="subtitle", uselist=False)

    def __repr__(self):
        return f"<Subtitle(id={self.id}, video_id={self.video_id}, language={self.language})>"


class GeneratedScript(Base):
    """生成的脚本表"""
    __tablename__ = "generated_scripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(255), nullable=False, comment='主题/关键词')
    platform = Column(Enum(Platform), nullable=False, comment='平台')
    content = Column(Text(length=4294967295), nullable=False, comment='脚本内容')
    video_count = Column(Integer, nullable=False, comment='涉及的视频数量')
    video_ids = Column(JSON, nullable=False, comment='相关视频ID列表')
    subtitle_ids = Column(JSON, nullable=False, comment='相关字幕ID列表')
    summary_ids = Column(JSON, nullable=False, comment='相关总结ID列表')
    
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<GeneratedScript(id={self.id}, topic='{self.topic}', platform={self.platform})>"

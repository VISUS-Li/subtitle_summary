from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from db.init.base import Base
import enum
import uuid


class Platform(enum.Enum):
    """视频平台"""
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"
    XIAOYUZHOU = "xiaoyuzhou"  # 添加小宇宙平台

    @classmethod
    def get_values(cls):
        return [member.value for member in cls]


class SubtitleSource(enum.Enum):
    """字幕来源类型"""
    OFFICIAL = "official"  # 官方外挂字幕
    WHISPER = "whisper"  # Whisper生成字幕

    @classmethod
    def get_values(cls):
        return [member.value for member in cls]


class Video(Base):
    """视频信息表"""
    __tablename__ = "videos"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))  # 内部ID
    platform = Column(String(20), nullable=False)  # 改为字符串存储

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

    def set_platform(self, platform: Platform):
        """设置平台"""
        self.platform = platform.value

    def get_platform(self) -> Platform:
        """获取平台枚举值"""
        return Platform(self.platform)


class TaskStatus(enum.Enum):
    """任务状态"""
    PENDING = "pending"    # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 完成
    FAILED = "failed"      # 失败

    @classmethod
    def get_values(cls):
        return [member.value for member in cls]


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
    status = Column(String(20), nullable=False, default=TaskStatus.PENDING.value)  # 改为字符串存储
    error_message = Column(Text, nullable=True)  # 错误信息
    retry_count = Column(Integer, default=0)     # 重试次数
    workflow_id = Column(String(64), nullable=True)  # Coze工作流ID
    last_retry_time = Column(DateTime, nullable=True)  # 上次重试时间

    # 新增关键点相关字段
    key_points = Column(JSON, nullable=True)  # 关键点列表
    association = Column(Boolean, nullable=True)  # 关联性判断
    score = Column(Float, nullable=True)  # 关联分数
    point_details = Column(Text(length=4294967295), nullable=True)  # 详细要点总结

    def set_status(self, status: TaskStatus):
        """设置状态"""
        self.status = status.value

    def get_status(self) -> TaskStatus:
        """获取状态枚举值"""
        return TaskStatus(self.status)


class Subtitle(Base):
    """字幕信息表"""
    __tablename__ = "subtitles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(64), ForeignKey("videos.id"), nullable=False)
    platform_vid = Column(String(64), nullable=False)
    platform = Column(String(20), nullable=False)  # 改为字符串存储
    source = Column(String(20), nullable=False)    # 改为字符串存储
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

    def set_platform(self, platform: Platform):
        """设置平台"""
        self.platform = platform.value

    def get_platform(self) -> Platform:
        """获取平台枚举值"""
        return Platform(self.platform)

    def set_source(self, source: SubtitleSource):
        """设置来源"""
        self.source = source.value

    def get_source(self) -> SubtitleSource:
        """获取来源枚举值"""
        return SubtitleSource(self.source)

    def __repr__(self):
        return f"<Subtitle(id={self.id}, video_id={self.video_id}, language={self.language})>"


class GeneratedScript(Base):
    """生成的脚本表"""
    __tablename__ = "generated_scripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String(255), nullable=False, comment='主题/关键词')
    platform = Column(String(20), nullable=False, comment='平台')  # 改为字符串存储
    content = Column(Text(length=4294967295), nullable=False, comment='脚本内容')
    video_count = Column(Integer, nullable=False, comment='涉及的视频数量')
    video_ids = Column(JSON, nullable=False, comment='相关视频ID列表')
    subtitle_ids = Column(JSON, nullable=False, comment='相关字幕ID列表')
    summary_ids = Column(JSON, nullable=False, comment='相关总结ID列表')
    
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_platform(self, platform: Platform):
        """设置平台"""
        self.platform = platform.value

    def get_platform(self) -> Platform:
        """获取平台枚举值"""
        return Platform(self.platform)

    def __repr__(self):
        return f"<GeneratedScript(id={self.id}, topic='{self.topic}', platform={self.platform})>"


def get_video_url(platform_vid: str, platform: Platform) -> str:
    """根据平台和视频ID生成视频URL
    
    Args:
        platform_vid: 平台视频ID
        platform: 平台类型
        
    Returns:
        str: 视频URL
    """
    if platform == Platform.YOUTUBE:
        return f"https://www.youtube.com/watch?v={platform_vid}"
    elif platform == Platform.BILIBILI:
        return f"https://www.bilibili.com/video/{platform_vid}"
    elif platform == Platform.XIAOYUZHOU:
        return f"https://www.xiaoyuzhoufm.com/episode/{platform_vid}"
    else:
        raise ValueError(f"不支持的平台: {platform}")

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

    def __repr__(self):
        return f"<Subtitle(id={self.id}, video_id={self.video_id}, language={self.language})>"

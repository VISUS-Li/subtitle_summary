from typing import List, Optional
from pydantic import BaseModel, Field


class SubtitleInput(BaseModel):
    """字幕处理输入参数"""
    topic: str = Field(..., description="本次总结围绕的主题")
    subtitle: str = Field(..., description="字幕内容")
    language: str = Field(..., description="字幕语言")
    title: str = Field(..., description="视频标题")
    source: str = Field(..., description="字幕来源", pattern="^(OFFICIAL|WHISPER)$")


class AssociationResult(BaseModel):
    """关联性分析结果"""
    association: bool = Field(..., description="是否关联")
    score: float = Field(..., description="关联分数", ge=0, le=100)


class SubtitlePoint(BaseModel):
    """字幕关键点"""
    key_point: List[str] = Field(..., description="关键点列表")


class PointSummary(BaseModel):
    """关键点总结"""
    point: str = Field(..., description="关键点")
    summary: str = Field(..., description="总结内容")


class SubtitleOutput(BaseModel):
    """字幕处理输出结果"""
    association_result: AssociationResult
    key_points: List[str]
    point_summaries: List[PointSummary]
    summarized_subtitle: str

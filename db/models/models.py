from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel

class ServiceConfig(BaseModel):
    """服务配置模型"""
    service_name: str
    config_key: str
    config_value: str
    updated_at: datetime = datetime.now()

class BiliConfig(BaseModel):
    """B站配置模型"""
    sessdata: str
    bili_jct: str
    buvid3: str

class YoutubeConfig(BaseModel):
    """YouTube配置模型"""
    api_key: Optional[str] = None
    # 可以根据需要添加更多YouTube相关配置

class WhisperConfig(BaseModel):
    """Whisper配置模型"""
    model_name: str
    language: str
    prompt: str

class SystemConfig(BaseModel):
    """系统配置模型"""
    max_retries: int
    retry_delay: int
    default_max_results: int

class DatabaseConfig(BaseModel):
    """数据库配置模型"""
    type: str  # 'sqlite', 'postgresql', 'mysql'
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: str
    charset: Optional[str] = 'utf8mb4'
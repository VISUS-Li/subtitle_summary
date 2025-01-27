from fastapi import APIRouter, HTTPException

from api.routers import bili
from db.models import WhisperConfig, SystemConfig
from db.database import Database
from services.bili2text.config import get_config
from typing import Dict

router = APIRouter(prefix="/config", tags=["config"])
db = Database()

@router.get("/system")
async def get_system_config() -> SystemConfig:
    """获取系统配置"""
    config = db.get_service_config("system", "config")
    if not config:
        # 返回默认配置
        config = {
            "max_retries": 3,
            "retry_delay": 5,
            "default_max_results": 5
        }
        db.set_service_config("system", "config", config)
    return SystemConfig(**config)

@router.post("/system")
async def set_system_config(config: SystemConfig):
    """设置系统配置"""
    try:
        db.set_service_config("system", "config", config.dict())
        # 重新加载配置
        new_config = get_config()
        return {"message": "系统配置更新成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/whisper")
async def get_whisper_config() -> WhisperConfig:
    """获取Whisper配置"""
    config = db.get_service_config("whisper", "config")
    if not config:
        # 返回默认配置
        config = {
            "model_name": "large-v3",
            "language": "zh",
            "prompt": "以下是普通话转写的文本，请使用规范的中文标点（，。！？），保留专业术语的英文缩写，并纠正同音错别字。语言中可能存在"
        }
        db.set_service_config("whisper", "config", config)
    return WhisperConfig(**config)

@router.post("/whisper")
async def set_whisper_config(config: WhisperConfig):
    """设置Whisper配置"""
    try:
        db.set_service_config("whisper", "config", config.dict())
        # 重新加载配置
        new_config = get_config()
        # 更新全局bili2text实例的配置
        if bili.bili2text_instance:
            bili.bili2text_instance.update_config(new_config)
        return {"message": "Whisper配置更新成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/all")
async def get_all_configs() -> Dict:
    """获取所有配置"""
    return {
        "system": await get_system_config(),
        "whisper": await get_whisper_config()
    } 
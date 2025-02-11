from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from db.models.service_config import ConfigCategory
from services.config_service import ConfigurationService

router = APIRouter(prefix="/config", tags=["config"])
config_service = ConfigurationService()

class ConfigValue(BaseModel):
    """配置值模型"""
    service_name: str
    config_key: str
    value: Any
    description: Optional[str] = None

@router.get("/services/{service_name}")
async def get_service_configs(service_name: str):
    """获取服务配置"""
    try:
        configs = config_service.get_all_service_configs_detail(service_name)
        return {"configs": configs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories/{category}")
async def get_category_configs(category: ConfigCategory):
    """获取分类配置"""
    try:
        configs = config_service.get_category_configs(category)
        return {"configs": configs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/set")
async def set_config(config: ConfigValue):
    """设置配置"""
    try:
        config_service.set_config(
            service_name=config.service_name,
            config_key=config.config_key,
            value=config.value,
            description=config.description
        )
        return {"message": "配置更新成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories")
async def get_all_categories():
    """获取所有配置分类"""
    return {"categories": [category.value for category in ConfigCategory]}

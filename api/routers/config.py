from typing import List, Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.routers import bili
from db.service_config import ServiceConfig
from services.bili2text.config import get_config

router = APIRouter(prefix="/config", tags=["config"])
db = ServiceConfig()


class ConfigValue(BaseModel):
    """配置值模型"""
    value: Any
    description: Optional[str] = None
    is_encrypted: Optional[bool] = False


class ConfigResponse(BaseModel):
    """配置响应模型"""
    service_name: str
    config_key: str
    value: Any
    value_type: str
    description: Optional[str]
    is_system: bool
    is_encrypted: bool
    created_at: str
    updated_at: str


class CookieConfig(BaseModel):
    """Cookie配置请求模型"""
    value: str
    description: str


@router.get("/services/{service_name}", response_model=List[ConfigResponse])
async def get_service_configs(service_name: str):
    """获取服务的所有配置"""
    try:
        configs = db.get_all_service_configs_detail(service_name)
        if not configs:  # 检查是否为空
            return []  # 返回空列表
        return configs
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/services/{service_name}/{config_key}", response_model=ConfigResponse)
async def get_service_config(service_name: str, config_key: str):
    """获取特定服务配置"""
    config = db.get_service_config_detail(service_name, config_key)
    if not config:
        raise HTTPException(
            status_code=404, 
            detail=f"未找到服务 {service_name} 的配置项 {config_key}"
        )
    return config


@router.post("/services/{service_name}/{config_key}")
async def set_service_config(
        service_name: str,
        config_key: str,
        config: ConfigValue
):
    """设置服务配置"""
    try:
        db.set_service_config(
            service_name=service_name,
            config_key=config_key,
            value=config.value,
            description=config.description,
            is_encrypted=config.is_encrypted
        )

        return {"message": "配置更新成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/services/{service_name}/{config_key}")
async def delete_service_config(service_name: str, config_key: str):
    """删除服务配置"""
    try:
        db.delete_service_config(service_name, config_key)
        return {"message": "配置删除成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

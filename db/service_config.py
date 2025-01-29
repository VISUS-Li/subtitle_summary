from typing import Optional, Dict, Any, List

from sqlalchemy import and_

from db.init.base import get_db
from db.init.manager import DatabaseManager
from db.models.service_config import ServiceConfig as ServiceConfigModel


class ServiceConfig:
    _instance = None
    _initialized = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(ServiceConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化数据库"""
        self.manager = DatabaseManager()


    # 服务配置相关方法
    def set_service_config(
            self,
            service_name: str,
            config_key: str,
            value: Any,
            description: str = None,
            is_encrypted: bool = False
    ) -> None:
        """设置服务配置"""
        with get_db() as db:
            config = db.query(ServiceConfigModel).filter(
                and_(
                    ServiceConfigModel.service_name == service_name,
                    ServiceConfigModel.config_key == config_key
                )
            ).first()

            if config:
                # 只更新发生变化的值
                if config.value != value:
                    config.value = value
                if description and config.description != description:
                    config.description = description
                if config.is_encrypted != is_encrypted:
                    config.is_encrypted = is_encrypted
            else:
                config = ServiceConfigModel.create_service_config(
                    service=service_name,
                    key=config_key,
                    value=value,
                    description=description,
                    is_encrypted=is_encrypted
                )
                db.add(config)
            
            # 只有当值发生变化时才更新缓存
            cache_key = (service_name, config_key)
            if self.manager._config_cache.get(cache_key) != value:
                self.manager._config_cache[cache_key] = value

    def get_service_config(self, service_name: str, config_key: str) -> Any:
        """获取服务配置（带缓存）"""
        # 优先从缓存获取
        cache_key = (service_name, config_key)
        cached_value = self.manager._config_cache.get(cache_key)

        if cached_value is not None:
            return cached_value

        # 缓存未命中时查询数据库
        with get_db() as db:
            config = db.query(ServiceConfigModel).filter(
                and_(
                    ServiceConfigModel.service_name == service_name,
                    ServiceConfigModel.config_key == config_key
                )
            ).first()
            
            if config:
                value = config.value
                # 更新缓存
                self.manager._config_cache[cache_key] = value
                return value
            
            return None  # 明确返回 None

    def get_service_config_detail(self, service_name: str, config_key: str) -> Optional[Dict]:
        """获取服务配置详情"""
        with get_db() as db:
            config = db.query(ServiceConfigModel).filter(
                and_(
                    ServiceConfigModel.service_name == service_name,
                    ServiceConfigModel.config_key == config_key
                )
            ).first()

            return config.to_dict() if config else None

    def get_all_service_configs(self, service_name: str) -> Dict[str, Any]:
        """获取服务的所有配置"""
        with get_db() as db:
            configs = db.query(ServiceConfigModel).filter(
                ServiceConfigModel.service_name == service_name
            ).all()

            if not configs:  # 检查是否为空
                return {}  # 返回空字典而不是None
            
            return {config.config_key: config.value for config in configs}

    def get_all_service_configs_detail(self, service_name: str) -> List[Dict]:
        """获取服务的所有配置详情"""
        with get_db() as db:
            configs = db.query(ServiceConfigModel).filter(
                ServiceConfigModel.service_name == service_name
            ).all()

            if not configs:  # 检查是否为空
                return []  # 返回空列表而不是None
            
            return [config.to_dict() for config in configs]

    def delete_service_config(self, service_name: str, config_key: str = None) -> None:
        """删除服务配置"""
        with get_db() as db:
            query = db.query(ServiceConfigModel).filter(
                ServiceConfigModel.service_name == service_name
            )

            if config_key:
                query = query.filter(ServiceConfigModel.config_key == config_key)

            query.delete()
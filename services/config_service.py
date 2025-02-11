from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from db.models.service_config import ServiceConfig, ConfigCategory
from db.init.default_config import DEFAULT_CONFIGS
from sqlalchemy import and_
import json


class ConfigurationService:
    """配置服务类"""
    _instance = None
    _config_cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        if not self._initialized:
            self._init_configs()
            self._initialized = True

    def _init_configs(self):
        """初始化配置"""
        from db.init.manager import DatabaseManager
        with DatabaseManager().SessionLocal() as db:
            self._sync_default_configs(db)

    def _sync_default_configs(self, db: Session):
        """同步默认配置到数据库"""
        for service_name, service_config in DEFAULT_CONFIGS.items():
            category = service_config["category"]
            configs = service_config["configs"]

            for config_key, config_data in configs.items():
                existing_config = db.query(ServiceConfig).filter(
                    and_(
                        ServiceConfig.service_name == service_name,
                        ServiceConfig.config_key == config_key
                    )
                ).first()

                if existing_config:
                    # 更新现有配置的描述
                    existing_config.description = config_data["description"]
                else:
                    # 创建新配置
                    category_enum = ConfigCategory(category)
                    new_config = ServiceConfig(
                        service_name=service_name,
                        config_key=config_key,
                        category=category_enum,
                        value=config_data["value"],
                        description=config_data["description"]
                    )
                    db.add(new_config)

            db.commit()
            self._refresh_cache(db)

    def _refresh_cache(self, db: Session):
        """刷新配置缓存"""
        configs = db.query(ServiceConfig).all()
        self._config_cache.clear()

        for config in configs:
            service_key = (config.service_name, config.config_key)
            self._config_cache[service_key] = config.value_text

    def _convert_value(self, value: Any) -> Any:
        """根据值的特征转换为适当的类型"""
        if value is None:
            return None
            
        # 如果已经是非字符串类型，直接返回
        if not isinstance(value, str):
            return value
            
        # 尝试转换为JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
            
        # 尝试转换为布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
            
        # 尝试转换为整数
        try:
            if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                return int(value)
        except ValueError:
            pass
            
        # 尝试转换为浮点数
        try:
            return float(value)
        except ValueError:
            pass
            
        # 如果无法转换，返回原始字符串
        return value

    def get_config(self, service_name: str, config_key: str) -> Any:
        """获取配置值"""
        cache_key = (service_name, config_key)
        if cache_key in self._config_cache:
            return self._convert_value(self._config_cache[cache_key])

        from db.init.manager import DatabaseManager
        with DatabaseManager().SessionLocal() as db:
            config = db.query(ServiceConfig).filter(
                ServiceConfig.service_name == service_name,
                ServiceConfig.config_key == config_key
            ).first()

            if config:
                self._config_cache[cache_key] = config.value
                return self._convert_value(config.value)

            # 如果数据库中不存在，返回默认配置
            if (service_name in DEFAULT_CONFIGS and
                    config_key in DEFAULT_CONFIGS[service_name]["configs"]):
                default_value = DEFAULT_CONFIGS[service_name]["configs"][config_key]["value"]
                return self._convert_value(default_value)

            return None

    def get_category_configs(self, category: ConfigCategory) -> Dict[str, Dict[str, Any]]:
        """获取分类的所有配置"""
        from db.init.manager import DatabaseManager
        with DatabaseManager().SessionLocal() as db:
            configs = db.query(ServiceConfig).filter(
                ServiceConfig.category == category
            ).all()

            result = {}
            for config in configs:
                if config.service_name not in result:
                    result[config.service_name] = {}
                result[config.service_name][config.config_key] = config.value
            return result

    def set_config(self, service_name: str, config_key: str, value: Any, description: Optional[str] = None):
        """设置配置值和描述"""
        from db.init.manager import DatabaseManager
        with DatabaseManager().SessionLocal() as db:
            config = db.query(ServiceConfig).filter(
                ServiceConfig.service_name == service_name,
                ServiceConfig.config_key == config_key
            ).first()

            if config:
                config.value = value
                if description is not None:
                    config.description = description
            else:
                if (service_name in DEFAULT_CONFIGS and
                        config_key in DEFAULT_CONFIGS[service_name]["configs"]):
                    category = DEFAULT_CONFIGS[service_name]["category"]
                    default_description = DEFAULT_CONFIGS[service_name]["configs"][config_key]["description"]
                    config = ServiceConfig(
                        service_name=service_name,
                        config_key=config_key,
                        category=category,
                        value=value,
                        description=description or default_description
                    )
                    db.add(config)
                else:
                    raise ValueError(f"配置项不存在: {service_name}.{config_key}")

            db.commit()
            self._config_cache[(service_name, config_key)] = value

    def get_all_service_configs_detail(self, service_name: str) -> dict[Any, dict[str, Any | None]]:
        """获取服务的所有配置详情"""
        from db.init.manager import DatabaseManager
        with DatabaseManager().SessionLocal() as db:
            configs = db.query(ServiceConfig).filter(
                ServiceConfig.service_name == service_name
            ).all()
            
            # 转换为字典格式，包含所有详细信息
            result = {}
            for config in configs:
                result[config.config_key] = {
                    "value": config.value,
                    "description": config.description,
                    "category": config.category.value if config.category else None,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None
                }
            return result

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
            
        # 预处理字符串
        def clean_json_string(s: str) -> str:
            # 移除首尾的单引号（如果存在）
            if s.startswith("'") and s.endswith("'"):
                s = s[1:-1]
            
            # 处理多行字符串，保留基本格式但移除多余空白
            lines = s.split('\n')
            cleaned_lines = []
            for line in lines:
                # 移除行首尾的空白字符
                line = line.strip()
                # 跳过空行
                if not line:
                    continue
                # 移除行尾的逗号（如果后面跟着 } 或 ]）
                if line.endswith(',') and any(next_char in ']}' for next_char in ''.join(lines[lines.index(line)+1:]).strip()):
                    line = line[:-1]
                cleaned_lines.append(line)
            
            # 重新组合成单个字符串
            s = ''.join(cleaned_lines)
            
            # 替换所有单引号为双引号（但不替换字符串内的单引号）
            in_string = False
            result = []
            i = 0
            while i < len(s):
                if s[i] == '\\':  # 处理转义字符
                    result.append(s[i:i+2])
                    i += 2
                    continue
                if s[i] == '"':
                    in_string = not in_string
                if s[i] == "'" and not in_string:
                    result.append('"')
                else:
                    result.append(s[i])
                i += 1
            
            return ''.join(result)

        # 尝试解析JSON
        try:
            cleaned_value = clean_json_string(value)
            return json.loads(cleaned_value)
        except json.JSONDecodeError:
            pass

        # 如果JSON解析失败，尝试其他类型转换
        processed_value = value.strip()
        
        # 尝试转换为布尔值    
        if processed_value.lower() in ('true', 'false'):
            return processed_value.lower() == 'true'
            
        # 尝试转换为整数
        try:
            if processed_value.isdigit() or (processed_value.startswith('-') and processed_value[1:].isdigit()):
                return int(processed_value)
        except ValueError:
            pass
            
        # 尝试转换为浮点数
        try:
            return float(processed_value)
        except ValueError:
            pass
            
        # 如果无法转换，返回原始字符串
        return value

    def get_config(self, service_name: str, config_key: str) -> Any:
        """获取配置值"""
        cache_key = (service_name, config_key)
        if cache_key in self._config_cache:
            value = self._config_cache[cache_key]
            return self._convert_value(value)

        from db.init.manager import DatabaseManager
        with DatabaseManager().SessionLocal() as db:
            config = db.query(ServiceConfig).filter(
                ServiceConfig.service_name == service_name,
                ServiceConfig.config_key == config_key
            ).first()

            if config:
                value = config.value
                self._config_cache[cache_key] = value
                return self._convert_value(value)

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

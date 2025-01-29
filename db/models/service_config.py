from datetime import datetime
from typing import Dict, Any
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, Enum
from sqlalchemy.ext.hybrid import hybrid_property
from db.init.base import Base
import enum


class ConfigValueType(enum.Enum):
    """配置值类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    PASSWORD = "password"  # 用于存储敏感信息


class ServiceConfig(Base):
    """服务配置模型"""
    __tablename__ = "service_configs"

    # 主键和分类字段
    service_name = Column(String(255), primary_key=True, comment='服务名称')
    config_key = Column(String(255), primary_key=True, comment='配置键名')

    # 配置值字段
    string_value = Column(Text, nullable=True, comment='字符串值')
    int_value = Column(Integer, nullable=True, comment='整数值')
    float_value = Column(Float, nullable=True, comment='浮点数值')
    bool_value = Column(Boolean, nullable=True, comment='布尔值')
    json_value = Column(Text, nullable=True, comment='JSON值')
    password_value = Column(Text, nullable=True, comment='密码/敏感信息')

    # 元数据字段
    value_type = Column(Enum(ConfigValueType), nullable=False, comment='值类型')
    description = Column(Text, nullable=True, comment='配置描述')
    is_system = Column(Boolean, default=False, comment='是否为系统配置')
    is_encrypted = Column(Boolean, default=False, comment='是否加密存储')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    @hybrid_property
    def value(self) -> Any:
        """获取配置值"""
        if self.value_type == ConfigValueType.STRING:
            return self.string_value
        elif self.value_type == ConfigValueType.INTEGER:
            return self.int_value
        elif self.value_type == ConfigValueType.FLOAT:
            return self.float_value
        elif self.value_type == ConfigValueType.BOOLEAN:
            return self.bool_value
        elif self.value_type == ConfigValueType.JSON:
            return self.json_value
        elif self.value_type == ConfigValueType.PASSWORD:
            return self.password_value
        return None

    @value.setter
    def value(self, value: Any):
        """设置配置值"""
        # 清空所有值字段
        self.string_value = None
        self.int_value = None
        self.float_value = None
        self.bool_value = None
        self.json_value = None
        self.password_value = None

        # 根据值类型设置相应字段
        if isinstance(value, str):
            self.value_type = ConfigValueType.STRING
            self.string_value = value
        elif isinstance(value, int):
            self.value_type = ConfigValueType.INTEGER
            self.int_value = value
        elif isinstance(value, float):
            self.value_type = ConfigValueType.FLOAT
            self.float_value = value
        elif isinstance(value, bool):
            self.value_type = ConfigValueType.BOOLEAN
            self.bool_value = value
        elif isinstance(value, (dict, list)):
            self.value_type = ConfigValueType.JSON
            self.json_value = value
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_name": self.service_name,
            "config_key": self.config_key,
            "value": self.value,
            "value_type": self.value_type.value,
            "description": self.description,
            "is_system": self.is_system,
            "is_encrypted": self.is_encrypted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def create_system_config(cls, key: str, value: Any, description: str = None) -> "ServiceConfig":
        """创建系统配置"""
        return cls(
            service_name="system",
            config_key=key,
            value=value,
            description=description,
            is_system=True
        )

    @classmethod
    def create_service_config(cls, service: str, key: str, value: Any,
                              description: str = None, is_encrypted: bool = False) -> "ServiceConfig":
        """创建服务配置"""
        return cls(
            service_name=service,
            config_key=key,
            value=value,
            description=description,
            is_encrypted=is_encrypted
        )

# 这里可以添加其他模型

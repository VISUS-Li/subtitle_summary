import json
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


class ConfigCategory(str, enum.Enum):
    """配置分类"""
    DOWNLOAD = "download"  # 下载相关配置
    API = "api"           # API相关配置
    MODEL = "model"       # 模型相关配置
    SYSTEM = "system"     # 系统相关配置


class ServiceConfig(Base):
    """服务配置模型"""
    __tablename__ = "service_configs"

    # 主键字段
    service_name = Column(String(255), primary_key=True, comment='服务名称')
    config_key = Column(String(255), primary_key=True, comment='配置键名')

    # 值字段
    value_text = Column(Text, nullable=True, comment='配置值(JSON格式)')
    
    # 元数据字段
    description = Column(Text, nullable=True, comment='配置描述')
    is_encrypted = Column(Boolean, default=False, comment='是否加密存储')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 分类字段
    category = Column(Enum(ConfigCategory), nullable=False, default=ConfigCategory.SYSTEM)

    @hybrid_property
    def value(self) -> Any:
        """获取配置值"""
        if self.value_text is None:
            return None
        try:
            # 检查value_text是否为str类型
            if not isinstance(self.value_text, str):
                return self.value_text
            return json.loads(self.value_text)
        except json.JSONDecodeError:
            return self.value_text

    @value.setter
    def value(self, value: Any):
        """设置配置值"""
        if value is None:
            self.value_text = None
        elif isinstance(value, (dict, list)):
            self.value_text = json.dumps(value)
        else:
            self.value_text = str(value)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_name": self.service_name,
            "config_key": self.config_key,
            "value": self.value,
            "description": self.description,
            "is_encrypted": self.is_encrypted,
            "category": self.category.value if self.category else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# 这里可以添加其他模型

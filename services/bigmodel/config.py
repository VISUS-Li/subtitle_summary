from typing import Dict, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import yaml

class CozeConfig(BaseModel):
    """Coze API配置"""
    base_url: str = Field(default="https://api.coze.cn", description="Coze API基础URL")
    app_id: str = Field(..., description="应用ID")
    public_key: str = Field(..., description="公钥ID")
    private_key_path: str = Field(..., description="私钥文件路径")
    http_timeout: int = Field(default=30, description="HTTP请求超时时间(秒)")
    workflow_ids: Dict[str, str] = Field(default_factory=dict, description="工作流ID映射")

class Config(BaseModel):
    """全局配置"""
    coze: CozeConfig

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "Config":
        """从YAML文件加载配置"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict) 
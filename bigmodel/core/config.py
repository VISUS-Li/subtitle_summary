from pydantic_settings import BaseSettings
from typing import Dict, Optional


class Settings(BaseSettings):
    # API Keys
    MOONSHOT_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    QWEN_API_KEY: Optional[str] = None
    MINIMAX_API_KEY: Optional[str] = None

    # Model configurations
    DEFAULT_MODEL: Optional[str] = "kimi"
    MODEL_CONFIGS: Dict = {
        "kimi": {
            "base_url": "https://api.moonshot.cn/v1",
            "model_name": "moonshot-v1-128k",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "model_name": "deepseek-chat",
        },
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_name": "qwen-max",
        },
        "qwen-deepseek": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_name": "deepseek-r1",
        },
        "minimax": {
            "base_url": "https://api.minimaxi.chat/v1",
            "model_name": "MiniMax-Text-01",
        }

    }


    # 工作流配置
    WORKFLOW_CONFIGS: Dict = {
        "qa": {
            "default_model": "kimi",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        # 可以添加其他工作流配置
    }

    class Config:
        env_file = ".env"


settings = Settings()

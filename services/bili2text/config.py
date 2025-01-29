import os
from pathlib import Path
from db.service_config import ServiceConfig

# 基础目录配置
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "outputs"
LOG_DIR = BASE_DIR / "logs"

# 创建必要的目录
for dir_path in [DOWNLOAD_DIR, OUTPUT_DIR, LOG_DIR]:
    os.makedirs(dir_path, exist_ok=True)


def get_config():
    """获取配置"""
    try:
        db = ServiceConfig()
        
        # 获取系统配置
        max_retries = db.get_service_config("system", "max_retries")
        retry_delay = db.get_service_config("system", "retry_delay")
        default_max_results = db.get_service_config("system", "default_max_results")
        
        # 获取Whisper配置
        model_name = db.get_service_config("whisper", "model_name")
        language = db.get_service_config("whisper", "language")
        prompt = db.get_service_config("whisper", "prompt")
        
    except Exception:
        # 如果数据库未初始化或出错，使用默认值
        max_retries = 3
        retry_delay = 5
        default_max_results = 5
        model_name = "large-v3"
        language = "zh"
        prompt = "以下是普通话转写的文本..."
    
    return {
        # 系统配置
        "MAX_RETRIES": max_retries or 3,
        "RETRY_DELAY": retry_delay or 5,
        "DEFAULT_MAX_RESULTS": default_max_results or 5,
        
        # Whisper配置
        "DEFAULT_WHISPER_MODEL": model_name or "large-v3",
        "DEFAULT_LANGUAGE": language or "zh",
        "DEFAULT_PROMPT": prompt or "以下是普通话转写的文本..."
    }


# 导出配置
config = get_config()
MAX_RETRIES = config["MAX_RETRIES"]
RETRY_DELAY = config["RETRY_DELAY"]
DEFAULT_MAX_RESULTS = config["DEFAULT_MAX_RESULTS"]
DEFAULT_WHISPER_MODEL = config["DEFAULT_WHISPER_MODEL"]
DEFAULT_LANGUAGE = config["DEFAULT_LANGUAGE"]
DEFAULT_PROMPT = config["DEFAULT_PROMPT"]

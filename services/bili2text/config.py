import os
from pathlib import Path
from db.database import Database

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
    db = Database()
    
    # 获取系统配置，如果不存在则使用默认值
    system_config = db.get_service_config("system", "config") or {
        "max_retries": 3,
        "retry_delay": 5,
        "default_max_results": 5
    }
    
    # 获取Whisper配置，如果不存在则使用默认值
    whisper_config = db.get_service_config("whisper", "config") or {
        "model_name": "large-v3",
        "language": "zh",
        "prompt": "以下是普通话转写的文本，请使用规范的中文标点（，。！？），保留专业术语的英文缩写，并纠正同音错别字。语言中可能存在"
    }
    
    return {
        # 系统配置
        "MAX_RETRIES": system_config["max_retries"],
        "RETRY_DELAY": system_config["retry_delay"],
        "DEFAULT_MAX_RESULTS": system_config["default_max_results"],
        
        # Whisper配置
        "DEFAULT_WHISPER_MODEL": whisper_config["model_name"],
        "DEFAULT_LANGUAGE": whisper_config["language"],
        "DEFAULT_PROMPT": whisper_config["prompt"]
    }

# 导出配置
config = get_config()
MAX_RETRIES = config["MAX_RETRIES"]
RETRY_DELAY = config["RETRY_DELAY"]
DEFAULT_MAX_RESULTS = config["DEFAULT_MAX_RESULTS"]
DEFAULT_WHISPER_MODEL = config["DEFAULT_WHISPER_MODEL"]
DEFAULT_LANGUAGE = config["DEFAULT_LANGUAGE"]
DEFAULT_PROMPT = config["DEFAULT_PROMPT"] 
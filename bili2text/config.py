import os
from pathlib import Path

# 基础配置
BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "outputs"
LOG_DIR = BASE_DIR / "logs"

# 下载器配置
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒
DEFAULT_MAX_RESULTS = 5

# Whisper配置
DEFAULT_WHISPER_MODEL = "small"
DEFAULT_LANGUAGE = "zh"
DEFAULT_PROMPT = "以下是普通话的句子。"

# 创建必要的目录
for dir_path in [DOWNLOAD_DIR, OUTPUT_DIR, LOG_DIR]:
    os.makedirs(dir_path, exist_ok=True) 
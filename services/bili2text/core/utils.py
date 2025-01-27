import logging
import time
from functools import wraps
from pathlib import Path
from typing import Callable, Any
from ..config import LOG_DIR

class WSLogHandler(logging.Handler):
    def __init__(self, task_manager, task_id):
        super().__init__()
        self.task_manager = task_manager
        self.task_id = task_id

    def emit(self, record):
        try:
            msg = self.format(record)
            self.task_manager.add_log(self.task_id, record.levelname, msg)
        except Exception:
            self.handleError(record)

def setup_logger(name: str, task_manager=None, task_id=None) -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 文件处理器
    log_file = LOG_DIR / f"{name}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # WebSocket处理器（如果提供了task_manager和task_id）
    if task_manager and task_id:
        ws_handler = WSLogHandler(task_manager, task_id)
        ws_handler.setLevel(logging.INFO)
        ws_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(ws_handler)
    
    # 格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def retry_on_failure(max_retries: int = 3, delay: int = 5) -> Callable:
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(delay)
            return None
        return wrapper
    return decorator 
import logging
import time
from functools import wraps
from pathlib import Path
from typing import Callable, Any
from ..config import LOG_DIR
import sys
import contextvars

# 保存原始的stdout和stderr
original_stdout = sys.stdout
original_stderr = sys.stderr

# 定义一个ContextVar来存储当前的task_id
current_task_id = contextvars.ContextVar('current_task_id', default=None)

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

class WSStream:
    """
    自定义的流类，用于重定向stdout和stderr到WebSocket。
    同时保持控制台输出。
    """
    def __init__(self, task_manager, original_stream):
        self.task_manager = task_manager
        self.original_stream = original_stream

    def write(self, message):
        # 首先写入到原始流（控制台）
        self.original_stream.write(message)
        
        try:
            # 然后发送到WebSocket
            task_id = current_task_id.get()
            if task_id and message.strip():  # 只有当message不为空时才发送
                # 将消息按行拆分，并逐行发送
                for line in message.strip().split('\n'):
                    if line.strip():  # 跳过空行
                        self.task_manager.add_log(task_id, "INFO", line)
        except Exception as e:
            # 如果获取task_id失败，只打印到控制台
            self.original_stream.write(f"WSStream error: {str(e)}\n")

    def flush(self):
        self.original_stream.flush()

def redirect_stdout_stderr(task_manager):
    """
    重定向sys.stdout和sys.stderr到自定义的WSStream。
    保持对原始流的引用以维持控制台输出。
    """
    # 只在第一次调用时重定向
    if not isinstance(sys.stdout, WSStream):
        sys.stdout = WSStream(task_manager, original_stdout)
    if not isinstance(sys.stderr, WSStream):
        sys.stderr = WSStream(task_manager, original_stderr)
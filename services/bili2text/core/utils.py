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
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    print(f"第 {attempt + 1}/{max_retries} 次尝试失败: {str(e)}", 
                          file=sys.stderr)
                    if attempt == max_retries - 1:
                        print(f"已达到最大重试次数 {max_retries}, 操作失败", 
                              file=sys.stderr)
                        raise last_exception
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
        # 确保始终写入到控制台
        self.original_stream.write(message)
        self.original_stream.flush()  # 立即刷新确保显示
        
        try:
            # 发送到WebSocket
            task_id = current_task_id.get()
            if task_id and message.strip():
                # 判断是否是错误消息
                level = "ERROR" if self.original_stream == original_stderr else "INFO"
                for line in message.strip().split('\n'):
                    if line.strip():
                        self.task_manager.add_log(task_id, level, line)
        except Exception as e:
            # 确保异常本身也被打印到控制台
            self.original_stream.write(f"WSStream error: {str(e)}\n")
            self.original_stream.flush()

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
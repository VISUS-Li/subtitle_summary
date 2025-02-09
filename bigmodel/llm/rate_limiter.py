from datetime import datetime, timedelta
import asyncio
from typing import Dict, Optional
import time
from collections import deque

class RateLimiter:
    """API 速率限制器"""
    def __init__(
        self,
        qps: float,
        tpm: int,
        max_retries: int = 3,
        retry_interval: float = 1.0
    ):
        self.qps = qps  # 每秒查询次数限制
        self.tpm = tpm  # 每分钟 token 处理量限制
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        
        # 用于追踪请求时间
        self.request_times = deque()
        # 用于追踪 token 使用量
        self.token_usage = deque()
        
        # 用于异步锁
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int) -> None:
        """获取执行许可"""
        async with self._lock:
            await self._wait_for_qps()
            await self._wait_for_tpm(tokens)
            
            # 记录本次请求
            current_time = datetime.now()
            self.request_times.append(current_time)
            self.token_usage.append((current_time, tokens))
            
            # 清理过期记录
            self._cleanup_records()
    
    async def _wait_for_qps(self) -> None:
        """等待直到满足 QPS 限制"""
        while True:
            current_time = datetime.now()
            # 清理超过1秒的请求记录
            while (self.request_times and 
                   (current_time - self.request_times[0]).total_seconds() > 1):
                self.request_times.popleft()
            
            if len(self.request_times) < self.qps:
                break
                
            await asyncio.sleep(0.1)
    
    async def _wait_for_tpm(self, tokens: int) -> None:
        """等待直到满足 TPM 限制"""
        while True:
            current_time = datetime.now()
            # 清理超过1分钟的 token 使用记录
            while (self.token_usage and 
                   (current_time - self.token_usage[0][0]).total_seconds() > 60):
                self.token_usage.popleft()
            
            # 计算当前分钟内的 token 使用量
            current_tpm = sum(tokens for _, t in self.token_usage)
            
            if current_tpm + tokens <= self.tpm:
                break
                
            await asyncio.sleep(1.0)
    
    def _cleanup_records(self) -> None:
        """清理过期记录"""
        current_time = datetime.now()
        # 清理超过1秒的请求记录
        while (self.request_times and 
               (current_time - self.request_times[0]).total_seconds() > 1):
            self.request_times.popleft()
            
        # 清理超过1分钟的 token 使用记录
        while (self.token_usage and 
               (current_time - self.token_usage[0][0]).total_seconds() > 60):
            self.token_usage.popleft()
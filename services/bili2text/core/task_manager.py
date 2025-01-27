from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
import time
import uuid
from .task_status import TaskStatus


@dataclass
class Task:
    status: TaskStatus
    progress: float = 0
    message: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None
    create_time: float = field(default_factory=time.time)
    update_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "create_time": self.create_time,
            "update_time": self.update_time,
            "end_time": self.end_time,
            "logs": self.logs
        }


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    def create_task(self, task_id: str) -> None:
        """创建新任务"""
        current_time = time.time()
        self.tasks[task_id] = Task(
            status=TaskStatus.PENDING.value,
            create_time=current_time,
            update_time=current_time
        )

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> None:
        """更新任务状态"""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        task.update_time = time.time()
        
        if status:
            try:
                task.status = TaskStatus(status.lower())
                if status.lower() in ['completed', 'failed']:
                    task.end_time = time.time()
            except ValueError as e:
                raise ValueError(f"Invalid status value: {status}")
                
        if progress is not None:
            task.progress = progress
        if message:
            task.message = message
        if result:
            task.result = result
        if error:
            task.error = error
            task.status = TaskStatus.FAILED.value
            task.end_time = time.time()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        return self.tasks[task_id].to_dict()

    def remove_task(self, task_id: str) -> None:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]

    def clean_old_tasks(self, max_age: int = 3600):
        """清理超过指定时间的已完成任务"""
        current_time = time.time()
        for task_id in list(self.tasks.keys()):
            task = self.tasks[task_id]
            if task.end_time and (current_time - task.end_time) > max_age:
                del self.tasks[task_id]

    def add_log(self, task_id: str, level: str, message: str) -> None:
        """添加日志记录"""
        if task_id not in self.tasks:
            return
            
        log_entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message
        }
        self.tasks[task_id].logs.append(log_entry)
        # 同时更新任务消息
        self.update_task(task_id, message=message)

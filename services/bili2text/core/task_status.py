from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    FAILED = "failed"

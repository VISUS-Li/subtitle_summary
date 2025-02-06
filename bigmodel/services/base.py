from abc import ABC, abstractmethod
from typing import Dict, Any
from langchain_core.language_models import BaseChatModel


class BaseWorkflow(ABC):
    def __init__(self, llm_provider: BaseChatModel):
        self.llm = llm_provider

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流"""
        pass

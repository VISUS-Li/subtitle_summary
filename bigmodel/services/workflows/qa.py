from typing import Dict, Any
from langchain_core.messages import HumanMessage

from bigmodel.services.base import BaseWorkflow
from ..workflow_registry import WorkflowRegistry


@WorkflowRegistry.register("qa")
class QAWorkflow(BaseWorkflow):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行问答工作流"""
        question = params.get("question")
        if not question:
            raise ValueError("Question is required")
            
        context = params.get("context", "")
        
        # 构建提示信息
        messages = [
            HumanMessage(content=f"Context: {context}\nQuestion: {question}")
        ]
        
        # 调用 LLM
        response = await self.llm._agenerate(messages)
        
        return {
            "answer": response.generations[0].message.content,
            "metadata": response.llm_output
        } 
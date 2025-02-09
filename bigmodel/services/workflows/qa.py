from typing import Dict, Any

from bigmodel.services.workflows.base import BaseWorkflow
from bigmodel.services.workflows.workflow_registry import WorkflowRegistry
from bigmodel.prompts.base import PromptTemplateRegistry
from bigmodel.prompts.constants import PromptTemplateType


@WorkflowRegistry.register("qa")
class QAWorkflow(BaseWorkflow):
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行问答工作流"""
        question = params.get("question")
        if not question:
            raise ValueError("Question is required")
            
        context = params.get("context", "")
        chat_history = params.get("chat_history", [])
        
        # 使用枚举类型选择模板
        template_id = (PromptTemplateType.QA_WITH_HISTORY 
                      if chat_history 
                      else PromptTemplateType.QA_BASIC)
        prompt_template = PromptTemplateRegistry.get_template(template_id)
        
        # 构建提示信息
        prompt_args = {
            "context": context,
            "question": question
        }
        
        if chat_history:
            prompt_args["chat_history"] = chat_history
            
        # 格式化提示词
        messages = prompt_template.prompt.format_messages(**prompt_args)
        
        # 调用 LLM
        response = await self.llm._agenerate(messages)
        
        return {
            "answer": response.generations[0].message.content,
            "metadata": response.llm_output
        } 
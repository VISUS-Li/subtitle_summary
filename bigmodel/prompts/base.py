from typing import Dict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel
from .constants import PromptTemplateType
from .templates_config import TEMPLATE_CONFIGS


class BasePromptTemplate(BaseModel):
    """提示词模板基类"""
    template_id: PromptTemplateType
    description: str
    prompt: ChatPromptTemplate

    class Config:
        arbitrary_types_allowed = True


class PromptTemplateRegistry:
    """提示词模板注册表"""
    _templates: Dict[PromptTemplateType, BasePromptTemplate] = {}

    @classmethod
    def register(cls, template: BasePromptTemplate):
        """注册提示词模板"""
        cls._templates[template.template_id] = template
        print("注册模板：", template.template_id)

    @classmethod
    def get_template(cls, template_id: PromptTemplateType) -> BasePromptTemplate:
        """获取提示词模板"""
        if template_id not in cls._templates:
            raise ValueError(f"Template {template_id} not found")
        return cls._templates[template_id]

    @classmethod
    def initialize_templates(cls):
        """初始化所有提示词模板"""
        for template_id, config in TEMPLATE_CONFIGS.items():
            messages = []
            
            # 添加system message
            if "system_message" in config:
                messages.append(("system", config["system_message"]))
            
            # 添加chat history
            if "variables" in config and "chat_history" in config["variables"]:
                messages.append(MessagesPlaceholder(variable_name="chat_history"))
            
            # 添加human message
            if "human_message" in config:
                messages.append(("human", config["human_message"]))

            # 创建提示词模板
            prompt = ChatPromptTemplate.from_messages(messages)

            # 注册模板
            template = BasePromptTemplate(
                template_id=template_id,
                description=config.get("description", ""),
                prompt=prompt
            )
            cls.register(template)

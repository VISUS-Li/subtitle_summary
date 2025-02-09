from enum import Enum, auto

class PromptTemplateType(str, Enum):
    """提示词模板类型"""
    JSON_INSTRUCTION = "json_instruction"
    # QA工作流提示词
    QA_BASIC = "qa_basic"
    QA_WITH_HISTORY = "qa_with_history"

    
    # 后续可以添加其他工作流的提示词类型
    SUBTITLE_ASSOCIATION = "subtitle_association"
    SUBTITLE_POINT = "subtitle_point"
    SUBTITLE_SUMMARY = "subtitle_summary"
    # ... 
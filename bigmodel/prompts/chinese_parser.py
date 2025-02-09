from typing import Any, Dict
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from pydantic import BaseModel

class ChinesePydanticOutputParser(PydanticOutputParser):
    """支持中文格式说明的Pydantic输出解析器"""
    
    def get_format_instructions(self) -> str:
        schema = self.pydantic_object.schema()
        
        # 构建更明确的示例，包含具体的数据类型说明
        format_instructions = (
            "请严格按照以下JSON格式输出结果，不要添加任何额外的字段或结构：\n\n"
            "1. 输出格式必须是完整的JSON\n"
            "2. 不要包含任何其他说明文字\n"
            "3. 字段名称必须完全匹配，不能增加或修改\n"
            "4. 数据类型必须严格遵循示例格式\n\n"
            "5. 警告！很重要的一点：如果是要求输出字符串数组，则严格输出字符串数组，而不是object数组，不要增加或删除字段，要求输出什么字段就输出什么字段！字符串数组没有字段名称，只有字符串数组\n"
            "标准输出格式示例：\n"
        )
        
        # 生成更具体的示例值
        example = {
            key: self._get_strict_example(field, key)
            for key, field in schema["properties"].items()
        }
        
        format_instructions += f"{example}\n\n"
        format_instructions += "字段说明：\n"
        
        # 添加更详细的字段说明
        for key, field in schema["properties"].items():
            desc = field.get("description", "")
            type_info = self._get_type_description(field)
            format_instructions += f"- {key}: {desc} ({type_info})\n"
            
        return format_instructions
    
    def _get_strict_example(self, field: Dict[str, Any], field_name: str) -> Any:
        """返回更具体的示例值"""
        field_type = field.get("type", "any")
        if field_type == "array":
            # 对于数组类型，明确指出元素类型
            items_type = field.get("items", {}).get("type", "string")
            if items_type == "string":
                return ["示例内容1", "示例内容2"]
        return self._get_type_example(field)
    
    def _get_type_description(self, field: Dict[str, Any]) -> str:
        """返回字段类型的详细描述"""
        field_type = field.get("type", "any")
        if field_type == "array":
            items_type = field.get("items", {}).get("type", "string")
            return f"数组类型，每个元素必须是{items_type}类型"
        return f"{field_type}类型"
    
    def _get_type_example(self, field: Dict[str, Any]) -> Any:
        """根据字段类型返回示例值"""
        field_type = field.get("type", "any")
        if field_type == "boolean":
            return True
        elif field_type == "number":
            return 85.5
        elif field_type == "integer":
            return 85
        elif field_type == "string":
            return "示例文本"
        elif field_type == "array":
            return ["示例项1", "示例项2"]
        elif field_type == "object":
            return {"key": "value"}
        return None

from typing import Dict, Type
from .base import OpenAICompatibleLLM

class ModelRegistry:
    _models: Dict[str, Type[OpenAICompatibleLLM]] = {}

    @classmethod
    def register(cls, model_id: str):
        def decorator(model_class: Type[OpenAICompatibleLLM]):
            cls._models[model_id] = model_class
            print("注册大模型：", model_id)
            return model_class
        return decorator

    @classmethod
    def get_model(cls, model_id: str) -> Type[OpenAICompatibleLLM]:
        if model_id not in cls._models:
            raise ValueError(f"Model {model_id} not found")
        return cls._models[model_id] 
from bigmodel.core.config import settings
from bigmodel.llm.base import OpenAICompatibleLLM
from bigmodel.llm.model_registry import ModelRegistry


@ModelRegistry.register("kimi")
class KimiLLM(OpenAICompatibleLLM):
    model_name: str = settings.MODEL_CONFIGS["kimi"]["model_name"]
    base_url: str = settings.MODEL_CONFIGS["kimi"]["base_url"]
    api_key: str = settings.MOONSHOT_API_KEY

    @property
    def _llm_type(self) -> str:
        return "kimi"


@ModelRegistry.register("deepseek")
class DeepseekLLM(OpenAICompatibleLLM):
    model_name: str = settings.MODEL_CONFIGS["deepseek"]["model_name"]
    base_url: str = settings.MODEL_CONFIGS["deepseek"]["base_url"]
    api_key: str = settings.DEEPSEEK_API_KEY

    @property
    def _llm_type(self) -> str:
        return "deepseek"


@ModelRegistry.register("qwen")
class QwenLLM(OpenAICompatibleLLM):
    model_name: str = settings.MODEL_CONFIGS["qwen"]["model_name"]
    base_url: str = settings.MODEL_CONFIGS["qwen"]["base_url"]
    api_key: str = settings.QWEN_API_KEY

    @property
    def _llm_type(self) -> str:
        return "qwen"

@ModelRegistry.register("qwen-deepseek")
class QwenDeepseekLLM(OpenAICompatibleLLM):
    model_name: str = settings.MODEL_CONFIGS["qwen-deepseek"]["model_name"]
    base_url: str = settings.MODEL_CONFIGS["qwen-deepseek"]["base_url"] 
    api_key: str = settings.QWEN_API_KEY

    @property
    def _llm_type(self) -> str:
        return "qwen-deepseek"

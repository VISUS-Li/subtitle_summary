from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from openai import AsyncOpenAI, OpenAI
from pydantic import Field, PrivateAttr


class BaseLLMProvider(BaseChatModel, ABC):
    @abstractmethod
    async def agenerate(
        self, 
        messages: List[BaseMessage], 
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """异步生成回复"""
        pass

    @abstractmethod
    def generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """同步生成回复"""
        pass 

class OpenAICompatibleLLM(BaseChatModel):
    """OpenAI 兼容的 LLM 基类,提供统一的接口实现"""
    
    # 必需的配置字段
    model_name: str = Field(..., description="模型名称")
    base_url: str = Field(..., description="API 基础URL") 
    api_key: str = Field(..., description="API密钥")
    
    # 可选配置
    temperature: float = Field(default=0.7, description="采样温度")
    
    # 私有客户端
    _sync_client: OpenAI = PrivateAttr()
    _async_client: AsyncOpenAI = PrivateAttr()
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        # 初始化API客户端
        self._sync_client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self._async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def _format_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """统一消息格式化"""
        role_map = {"human": "user", "ai": "assistant", "system": "system"}
        return [{"role": role_map[msg.type], "content": msg.content} for msg in messages]

    def _create_chat_result(self, response: Any) -> ChatResult:
        """统一创建 ChatResult"""
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content=response.choices[0].message.content),
                    generation_info=dict(finish_reason=response.choices[0].finish_reason)
                )
            ],
            llm_output={"model_name": self.model_name}
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """同步生成回复"""
        try:
            response = self._sync_client.chat.completions.create(
                model=self.model_name,
                messages=self._format_messages(messages),
                temperature=kwargs.get("temperature", self.temperature),
                stream=kwargs.get("stream", False)
            )
            return self._create_chat_result(response)
        except Exception as e:
            print(f"同步生成回复出错: {str(e)}")
            raise

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """异步生成回复"""
        try:
            response = await self._async_client.chat.completions.create(
                model=self.model_name,
                messages=self._format_messages(messages),
                temperature=kwargs.get("temperature", self.temperature),
                stream=kwargs.get("stream", False)
            )
            return self._create_chat_result(response)
        except Exception as e:
            print(f"异步生成回复出错: {str(e)}")
            raise

    def stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Iterator[ChatResult]:
        """流式生成回复"""
        try:
            response = self._sync_client.chat.completions.create(
                model=self.model_name,
                messages=self._format_messages(messages),
                temperature=kwargs.get("temperature", self.temperature),
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield ChatResult(
                        generations=[
                            ChatGeneration(
                                message=AIMessage(content=chunk.choices[0].delta.content),
                                generation_info=dict(finish_reason=chunk.choices[0].finish_reason)
                            )
                        ],
                        llm_output={"model_name": self.model_name}
                    )
        except Exception as e:
            print(f"流式生成回复出错: {str(e)}")
            raise

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """获取模型标识参数"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
        } 
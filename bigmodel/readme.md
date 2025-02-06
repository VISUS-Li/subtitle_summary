# BigModel 服务使用文档

## 目录
- [简介](#简介)
- [快速开始](#快速开始) 
- [配置说明](#配置说明)
- [API 使用](#api-使用)
- [扩展指南](#扩展指南)

## 简介

BigModel 是一个基于 FastAPI 和 LangChain 构建的大模型服务框架，支持多种 LLM 模型接入和自定义工作流程。目前支持的模型包括:

- Kimi (Moonshot)
- Deepseek  
- Qwen (通义千问)
- MiniMax

## 快速开始

### 1. 环境配置

创建 `.env` 文件并配置以下环境变量:
env
MOONSHOT_API_KEY=your_moonshot_key
DEEPSEEK_API_KEY=your_deepseek_key
QWEN_API_KEY=your_qwen_key
MINIMAX_API_KEY=your_minimax_key

### 2. 启动服务

```bash
python bigmodel/main.py
```

服务将在 `http://localhost:8000` 启动。


## 配置说明

配置文件位于 `bigmodel/core/config.py`，你可以在这里：

- 设置默认模型
- 配置模型参数  
- 添加工作流配置
```python
DEFAULT_MODEL = "kimi" # 设置默认模型
MODEL_CONFIGS = {
"kimi": {
"base_url": "https://api.moonshot.cn/v1",
"model_name": "moonshot-v1-128k",
},
# ... 其他模型配置
}
```

```python
WORKFLOW_CONFIGS = {
"qa": {
"default_model": "kimi",
"temperature": 0.7,
"max_tokens": 1000
},

# ... 其他工作流配置
}
```

## API 使用

### 执行工作流
``` http
POST /api/v1/workflow
请求体:
{
"workflow_id": "qa", # 工作流ID
"model_name": "kimi", # 可选，默认使用配置中的DEFAULT_MODEL
"params": {
"question": "你的问题",
"context": "可选的上下文"
}
}
响应:
{
"answer": "模型回答的内容",
"metadata": {
"model_name": "使用的模型名称"
}
}
```

## 扩展指南

### 1. 添加新的模型

1. 在 `bigmodel/core/config.py` 中添加模型配置：
```python
@ModelRegistry.register("new_model")
class NewModelLLM(OpenAICompatibleLLM):
model_name: str = settings.MODEL_CONFIGS["new_model"]["model_name"]
base_url: str = settings.MODEL_CONFIGS["new_model"]["base_url"]
api_key: str = settings.NEW_MODEL_API_KEY

@property
def llm_type(self) -> str:
return "new_model"
```

### 2. 添加新的工作流

1. 在 `bigmodel/services/workflows/` 目录下创建新的工作流文件：
``` python
from bigmodel.services.base import BaseWorkflow
from bigmodel.services.workflow_registry import WorkflowRegistry
@WorkflowRegistry.register("new_workflow")
class NewWorkflow(BaseWorkflow):
async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
# 实现工作流逻辑
return {
"result": "工作流执行结果"
}
```
2. 在 `bigmodel/core/config.py` 中添加工作流配置：
``` python
WORKFLOW_CONFIGS = {
"new_workflow": {
"default_model": "kimi",
"temperature": 0.7,
# ... 其他配置参数
}

}
```

## 注意事项

1. 所有新添加的模型必须兼容 OpenAI API 格式
2. 确保在添加新模型时在环境变量中配置相应的 API KEY
3. 工作流必须继承 `BaseWorkflow` 类并实现 `execute` 方法
4. 建议在添加新功能时编写相应的单元测试

## 错误处理

服务会返回以下 HTTP 状态码：

- 400: 请求参数错误
- 404: API 端点未找到  
- 500: 服务器内部错误

每个错误响应都会包含详细的错误信息，便于调试和问题排查。
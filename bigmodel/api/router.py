from typing import Dict, Any

import openai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bigmodel.core.config import settings
from bigmodel.llm.model_registry import ModelRegistry
from bigmodel.services.workflows.workflow_registry import WorkflowRegistry

router = APIRouter()


class WorkflowRequest(BaseModel):
    workflow_id: str
    params: Dict[str, Any]
    model_name: str


@router.post("/workflow")
async def execute_workflow(request: WorkflowRequest):
    try:
        # 获取模型实例
        model_class = ModelRegistry.get_model(request.model_name or settings.DEFAULT_MODEL)
        model_instance = model_class()

        # 获取工作流实例
        workflow_class = WorkflowRegistry.get_workflow(request.workflow_id)
        workflow = workflow_class(model_instance)

        # 执行工作流
        result = await workflow.execute(request.params)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except openai.NotFoundError as e:
        raise HTTPException(status_code=404, detail=f"API endpoint not found: {str(e)}")
    except openai.APIError as e:
        raise HTTPException(status_code=500, detail=f"API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

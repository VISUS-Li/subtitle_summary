from typing import Dict, Type
from bigmodel.services.workflows.base import BaseWorkflow


class WorkflowRegistry:
    _workflows: Dict[str, Type[BaseWorkflow]] = {}

    @classmethod
    def register(cls, workflow_id: str):
        def decorator(workflow_class: Type[BaseWorkflow]):
            cls._workflows[workflow_id] = workflow_class
            print("注册工作流：", workflow_id)
            return workflow_class

        return decorator

    @classmethod
    def get_workflow(cls, workflow_id: str) -> Type[BaseWorkflow]:
        if workflow_id not in cls._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        return cls._workflows[workflow_id]

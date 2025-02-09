from fastapi import FastAPI
from api.router import router
from prompts.base import PromptTemplateRegistry
from prompts.constants import PromptTemplateType

app = FastAPI(title="LangChain Workflow Service")


app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

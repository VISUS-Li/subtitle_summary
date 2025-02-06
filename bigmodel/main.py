from fastapi import FastAPI

from api.router import router

app = FastAPI(title="LangChain Workflow Service")

app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
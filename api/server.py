from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routers import bili, config
import logging
from services.bili2text.core.task_manager import TaskManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建全局task_manager实例
task_manager = TaskManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("正在初始化B站服务...")
    bili.init_bili_service(task_manager)
    logger.info("B站服务初始化完成")
    # 未来可以添加YouTube服务的初始化
    yield
    logger.info("服务关闭...")
    # 关闭时执行的代码（如果需要）可以放在这里


app = FastAPI(
    title="Video2Text API",
    description="视频字幕获取服务",
    lifespan=lifespan
)

# 将task_manager添加到app的state中，使其在其他地方可用
app.state.task_manager = task_manager

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(bili.router)
app.include_router(config.router)

# app.include_router(youtube.router)

if __name__ == "__main__":
    logger.info("启动服务器 http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

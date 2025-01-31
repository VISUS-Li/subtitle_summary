from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.bili2text.core.downloader import AudioDownloader
from services.bili2text.core.transcriber import AudioTranscriber
import uvicorn
from api.routers import bili, config, youtube
from services.bili2text.core.task_manager import TaskManager
from services.bili2text.core.utils import redirect_stdout_stderr
from services.bili2text.core.video_processor import VideoProcessor

# 创建全局task_manager实例
task_manager = TaskManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("正在初始化服务...")
    downloader = AudioDownloader()
    transcriber = AudioTranscriber()
    video_processor = VideoProcessor(downloader, transcriber)
    bili.init_bili_processor(video_processor)
    youtube.init_youtube_processor(video_processor)
    print("服务初始化完成")
    
    # 重定向标准输出和错误输出
    redirect_stdout_stderr(task_manager)
    
    yield
    print("服务关闭...")
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
app.include_router(youtube.router)

# app.include_router(youtube.router)

if __name__ == "__main__":
    print("启动服务器 http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

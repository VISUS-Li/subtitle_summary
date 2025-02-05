import time

print(f"[{time.time()}] 开始导入模块...")

start_time = time.time()
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

print(f"[{time.time()}] FastAPI相关模块导入完成，耗时: {time.time() - start_time:.2f}秒")

start_time = time.time()
from services.bili2text.core.downloader import AudioDownloader

print(f"[{time.time()}] AudioDownloader模块导入完成，耗时: {time.time() - start_time:.2f}秒")

start_time = time.time()
from services.bili2text.core.transcriber import AudioTranscriber

print(f"[{time.time()}] AudioTranscriber模块导入完成，耗时: {time.time() - start_time:.2f}秒")

start_time = time.time()
import uvicorn
from api.routers import bili, config, youtube, video

print(f"[{time.time()}] 路由模块导入完成，耗时: {time.time() - start_time:.2f}秒")

start_time = time.time()
from services.bili2text.core.task_manager import TaskManager
from services.bili2text.core.utils import redirect_stdout_stderr
from services.bili2text.core.video_processor import VideoProcessor
import os

print(f"[{time.time()}] 其他核心模块导入完成，耗时: {time.time() - start_time:.2f}秒")

# 创建全局task_manager实例
task_manager = TaskManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("正在初始化服务...")
    config_path = os.getenv("CONFIG_PATH", "config/config.yaml")

    start_time = time.time()
    downloader = AudioDownloader(config_path)
    print(f"下载器初始化耗时: {time.time() - start_time:.2f}秒")

    start_time = time.time()
    transcriber = AudioTranscriber()
    print(f"转写器初始化耗时: {time.time() - start_time:.2f}秒")

    start_time = time.time()
    video_processor = VideoProcessor(downloader, transcriber)
    print(f"视频处理器初始化耗时: {time.time() - start_time:.2f}秒")

    start_time = time.time()
    bili.init_bili_processor(video_processor)
    print(f"B站处理器初始化耗时: {time.time() - start_time:.2f}秒")

    start_time = time.time()
    youtube.init_youtube_processor(video_processor)
    print(f"YouTube处理器初始化耗时: {time.time() - start_time:.2f}秒")
    video.init_video_processor(video_processor)  # 初始化视频处理器
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
app.include_router(video.router)

# app.include_router(youtube.router)

if __name__ == "__main__":
    print("启动服务器 http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

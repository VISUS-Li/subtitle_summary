import time
import sys
from typing import List, Optional
from db.models.subtitle import SubtitleSource, Platform
from services.bili2text.config import get_config
from services.bili2text.core.utils import retry_on_failure
from services.bili2text.config import OUTPUT_DIR


class AudioTranscriber:
    """音频转写器,负责将音频转写为文本"""

    def __init__(self, config=None):
        """初始化转写器
        
        Args:
            config: 配置信息,为None时使用默认配置
        """
        self.output_dir = OUTPUT_DIR
        self._whisper = None
        self._model = None
        self.current_model_name = None
        self.config = config or get_config()
        self._subtitle_manager = None

    @property
    def whisper(self):
        if self._whisper is None:
            start_time = time.time()
            print(f"[{time.time()}] 开始导入 whisper 模块...")
            import whisper
            self._whisper = whisper
            print(f"[{time.time()}] whisper 模块导入完成，耗时: {time.time() - start_time:.2f}秒")
        return self._whisper

    def load_model(self, model_name: str):
        """加载Whisper模型
        
        Args:
            model_name: 模型名称
        """
        # 如果模型名称改变,重新加载模型
        if self._model is None or self.current_model_name != model_name:
            start_time = time.time()
            print(f"[{time.time()}] 开始加载 whisper 模型：{model_name}")
            device = "cuda" if self.whisper.torch.cuda.is_available() else "cpu"
            print(f"[{time.time()}] 检测到的设备: {device}")
            if device == "cuda":
                print(f"[{time.time()}] GPU信息: {self.whisper.torch.cuda.get_device_name(0)}")

            self._model = self.whisper.load_model(
                model_name,
                device=device
            )
            self.current_model_name = model_name
            print(f"[{time.time()}] whisper 模型加载完成，耗时: {time.time() - start_time:.2f}秒")

            print(f"模型所在设备: {next(self._model.parameters()).device}")

    @retry_on_failure(max_retries=3, delay=5)
    async def transcribe_file(self, topic: str, audio_path: str, video_id: str, platform: Platform) -> Optional[str]:
        """转录单个音频文件
        
        Args:
            audio_path: 音频文件路径
            video_id: 视频ID
            platform: 平台
            task_id: 任务ID(可选)
            
        Returns:
            Optional[str]: 转录文本,失败返回None
            
        Raises:
            Exception: 转录失败
        """
        try:
            # 获取视频信息以显示标题
            video_info = self._subtitle_manager.get_video_info(platform, video_id)
            video_title = f"「{video_info['title']}」" if video_info and video_info.get('title') else ''
            print(f"开始转录音频文件 [{platform.value}] {video_id} {video_title}")

            # 使用配置中的值
            model_name = self.config["DEFAULT_WHISPER_MODEL"]
            language = self.config["DEFAULT_LANGUAGE"]
            prompt = self.config["DEFAULT_PROMPT"]

            # 加载模型
            self.load_model(model_name)
            print("正在使用Whisper模型进行转录...")

            # 使用whisper进行转录
            result = self._model.transcribe(
                str(audio_path),
                initial_prompt=prompt,
                language=language,
                temperature=0.2,
                beam_size=5,
                fp16=True,
                condition_on_previous_text=False,
                verbose=True
            )

            print("转录完成,正在保存结果...")
            # 调用函数转换
            webvtt_result = self.convert_to_webvtt(result)

            # 打印转换后的结果
            print(webvtt_result)

            # 保存字幕
            try:
                await self._subtitle_manager.save_subtitle(
                    topic=topic,
                    video_id=video_id,
                    content=result["text"],
                    timed_content=webvtt_result,
                    source=SubtitleSource.WHISPER,
                    platform=platform,
                    platform_vid=video_id,
                    language=language,
                    model_name=model_name,
                )
            except Exception as e:
                print(f"保存字幕失败: {str(e)}")
                raise

            print("转录结果已保存")

            return result["text"]

        except Exception as e:
            error_msg = f"转录失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def convert_to_webvtt(self, result):
        """
        将whisper转录结果转换为WebVTT格式字幕
        
        Args:
            result: whisper转录的结果字典
            
        Returns:
            dict: WebVTT格式的字幕字典
        """
        webvtt = {
            "type": "webvtt",
            "metadata": {
                "kind": "captions",
                "language": "en-US" if result["language"] == "en" else result["language"] + "-" + result[
                    "language"].upper()
            },
            "segments": []
        }

        # 转换每个片段
        for segment in result["segments"]:
            webvtt["segments"].append({
                "start": round(segment["start"], 2),
                "end": round(segment["end"], 2),
                "text": segment["text"]
            })

        return webvtt

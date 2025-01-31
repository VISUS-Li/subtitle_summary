import sys
from typing import List, Optional

import whisper

from db.models.subtitle import SubtitleSource, Platform
from services.bili2text.config import get_config
from services.bili2text.core.subtitle_manager import SubtitleManager
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
        self.model = None
        self.current_model_name = None
        self.config = config or get_config()
        self.subtitle_manager = SubtitleManager()

    def load_model(self, model_name: str):
        """加载Whisper模型
        
        Args:
            model_name: 模型名称
        """
        # 如果模型名称改变,重新加载模型
        if self.model is None or self.current_model_name != model_name:
            print(f"正在加载whisper模型：{model_name}")
            device = "cuda" if whisper.torch.cuda.is_available() else "cpu"
            print(f"检测到的设备: {device}")
            if device == "cuda":
                print(f"GPU信息: {whisper.torch.cuda.get_device_name(0)}")

            self.model = whisper.load_model(
                model_name,
                device=device
            )
            self.current_model_name = model_name
            print("whisper模型加载成功")

            print(f"模型所在设备: {next(self.model.parameters()).device}")

    @retry_on_failure(max_retries=3, delay=5)
    def transcribe_file(self, audio_path: str, video_id: str, platform: Platform) -> Optional[str]:
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
            print(f"开始转录音频文件: {audio_path}")

            # 使用配置中的值
            model_name = self.config["DEFAULT_WHISPER_MODEL"]
            language = self.config["DEFAULT_LANGUAGE"]
            prompt = self.config["DEFAULT_PROMPT"]

            # 加载模型
            self.load_model(model_name)
            print("正在使用Whisper模型进行转录...")

            # 使用whisper进行转录
            result = self.model.transcribe(
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
            self.subtitle_manager.save_subtitle(
                video_id=video_id,
                content=result["text"],
                timed_content=result['segments'],
                source=SubtitleSource.WHISPER,
                platform=platform,
                platform_vid=video_id,
                language=language,
                model_name=model_name,
            )

            print("转录结果已保存")



            return result["text"]

        except Exception as e:
            error_msg = f"转录失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def transcribe_files(
            self,
            audio_paths: List[str],
            video_ids: List[str],
            platform: Platform,
            task_id: str = None
    ) -> List[str]:
        """转录多个音频文件
        
        Args:
            audio_paths: 音频文件路径列表
            video_ids: 视频ID列表
            platform: 平台
            task_id: 任务ID(可选)
            
        Returns:
            List[str]: 转录文本列表
        """
        output_files = []
        total = len(audio_paths)

        for i, (audio_path, video_id) in enumerate(zip(audio_paths, video_ids), 1):
            try:
                print(f"处理第 {i}/{total} 个文件: {audio_path}")
                output_text = self.transcribe_file(
                    audio_path,
                    video_id,
                    platform
                )
                if output_text:
                    output_files.append(output_text)
                print(f"进度: {i}/{total}")
            except Exception as e:
                print(f"转录文件失败 {audio_path}: {str(e)}")
                continue

        return output_files

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
                "language": "en-US" if result["language"] == "en" else result["language"] + "-" + result["language"].upper()
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

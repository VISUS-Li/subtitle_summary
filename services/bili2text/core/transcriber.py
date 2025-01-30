from typing import List, Optional
import whisper
from pathlib import Path
import sys

from db.models.subtitle import SubtitleSource, Platform
from ..config import OUTPUT_DIR
from .utils import retry_on_failure
from .task_status import TaskStatus
from services.bili2text.config import get_config
from services.bili2text.core.subtitle_manager import SubtitleManager


class AudioTranscriber:
    def __init__(self, task_manager=None, config=None):
        self.output_dir = OUTPUT_DIR
        self.model = None
        self.current_model_name = None
        self.task_manager = task_manager
        self.config = config or get_config()
        self.subtitle_manager = SubtitleManager()
        
    def update_config(self, new_config):
        """更新配置"""
        self.config = new_config
        # 如果模型配置改变，将current_model_name设为None以触发重新加载
        if self.current_model_name != new_config["DEFAULT_WHISPER_MODEL"]:
            self.current_model_name = None
            self.model = None
        
    def load_model(self, model_name: str):
        """加载Whisper模型"""
        # 如果模型名称改变，重新加载模型
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
    def transcribe_file(self, audio_path: str, video_id: str, platform: Platform, task_id: str = None) -> Optional[str]:
        """转录单个音频文件"""
        try:
            print(f"开始转录音频文件: {audio_path}")
            
            # 使用配置中的值
            model_name = self.config["DEFAULT_WHISPER_MODEL"]
            language = self.config["DEFAULT_LANGUAGE"]
            prompt = self.config["DEFAULT_PROMPT"]
            
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
            
            print("转录完成，正在保存结果...")
            
            # 保存字幕
            self.subtitle_manager.save_subtitle(
                video_id=video_id,
                content=result,
                source=SubtitleSource.WHISPER,
                platform=platform,
                platform_vid=video_id,
                language=language,
                model_name=model_name
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
        """转录多个音频文件"""
        output_files = []
        
        for i, audio_path in enumerate(audio_paths):
            try:
                output_file = self.transcribe_file(
                    audio_path,
                    video_ids[i],
                    platform,
                    task_id
                )
                if output_file:
                    output_files.append(output_file)
            except Exception as e:
                print(f"转录文件失败 {audio_path}: {str(e)}")
                continue
                
        return output_files 
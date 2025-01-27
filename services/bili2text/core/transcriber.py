from typing import List, Optional
import whisper
from pathlib import Path
from ..config import OUTPUT_DIR
from .utils import retry_on_failure
from .task_status import TaskStatus
from services.bili2text.config import get_config


class AudioTranscriber:
    def __init__(self, task_manager=None, config=None):
        self.output_dir = OUTPUT_DIR
        self.model = None
        self.current_model_name = None
        self.task_manager = task_manager
        self.config = config or get_config()
        
    def update_config(self, new_config):
        """更新配置"""
        self.config = new_config
        # 如果模型配置改变，将current_model_name设为None以触发重新加载
        if self.current_model_name != new_config["DEFAULT_WHISPER_MODEL"]:
            self.current_model_name = None
            self.model = None
        
    def load_model(self, model_name: str, task_id: str = None):
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
    def transcribe_file(
        self, 
        audio_path: str, 
        task_id: str = None,
        model_name: str = None,
        language: str = None,
        prompt: str = None
    ) -> Optional[str]:
        """转录单个音频文件"""
        # 使用配置中的值或传入的参数
        model_name = model_name or self.config["DEFAULT_WHISPER_MODEL"]
        language = language or self.config["DEFAULT_LANGUAGE"]
        prompt = prompt or self.config["DEFAULT_PROMPT"]
        
        self.load_model(model_name, task_id)
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            error = FileNotFoundError(f"音频文件不存在: {audio_path}")
            if task_id and self.task_manager:
                print(f"Task {task_id}: 音频文件不存在: {audio_path}")
            raise error
            
        print(f"开始转录音频: {audio_path}")
        
        try:
            if task_id and self.task_manager:
                print(f"Task {task_id}: 开始转录音频...")
            
            # 使用transcribe进行转录
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
            
            text = result["text"]
            output_path = self.output_dir / f"{audio_path.stem}.txt"
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
                
            if task_id and self.task_manager:
                print(f"Task {task_id}: 转录完成")
                
            print(f"转录完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"转录失败: {str(e)}")
            if task_id and self.task_manager:
                print(f"Task {task_id}: 转录失败: {str(e)}")
            raise

    def transcribe_files(
        self, 
        audio_paths: List[str], 
        model_name: str = "large-v3",
        language: str = "zh",
        prompt: str = ""
    ) -> List[str]:
        """转录多个音频文件"""
        output_files = []
        
        for audio_path in audio_paths:
            try:
                output_file = self.transcribe_file(
                    audio_path,
                    model_name=model_name,
                    language=language,
                    prompt=prompt
                )
                if output_file:
                    output_files.append(output_file)
            except Exception as e:
                print(f"转录文件失败 {audio_path}: {str(e)}")
                continue
                
        return output_files 
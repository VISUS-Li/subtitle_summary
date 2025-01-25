from typing import List, Optional
import whisper
from pathlib import Path
from bili2text.config import OUTPUT_DIR, DEFAULT_WHISPER_MODEL, DEFAULT_PROMPT
from bili2text.core.utils import setup_logger, retry_on_failure

logger = setup_logger("transcriber")

class AudioTranscriber:
    def __init__(self, model_name: str = DEFAULT_WHISPER_MODEL):
        self.model_name = model_name
        self.model = None
        self.output_dir = OUTPUT_DIR
        
    def load_model(self):
        """加载Whisper模型"""
        if self.model is None:
            # 添加GPU检测日志
            device = "cuda" if whisper.torch.cuda.is_available() else "cpu"
            logger.info(f"检测到的设备: {device}")
            if device == "cuda":
                logger.info(f"GPU信息: {whisper.torch.cuda.get_device_name(0)}")
            
            logger.info(f"加载Whisper模型: {self.model_name}")
            self.model = whisper.load_model(
                self.model_name,
                device=device
            )
            # 验证模型是否确实在GPU上
            logger.info(f"模型所在设备: {next(self.model.parameters()).device}")
            
    @retry_on_failure(max_retries=3, delay=5)
    def transcribe_file(self, audio_path: str, prompt: str = DEFAULT_PROMPT) -> Optional[str]:
        """转录单个音频文件"""
        self.load_model()
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            logger.error(f"音频文件不存在: {audio_path}")
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
        logger.info(f"开始转录音频: {audio_path}")
        
        try:
            result = self.model.transcribe(str(audio_path), initial_prompt=prompt)
            text = "".join([segment["text"] for segment in result["segments"] if segment])
            
            # 保存转录结果
            output_path = self.output_dir / f"{audio_path.stem}.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
                
            logger.info(f"转录完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"转录失败: {str(e)}")
            raise
            
    def transcribe_files(self, audio_paths: List[str], prompt: str = DEFAULT_PROMPT) -> List[str]:
        """转录多个音频文件"""
        output_files = []
        
        for audio_path in audio_paths:
            try:
                output_file = self.transcribe_file(audio_path, prompt)
                if output_file:
                    output_files.append(output_file)
            except Exception as e:
                logger.error(f"转录文件失败 {audio_path}: {str(e)}")
                continue
                
        return output_files 
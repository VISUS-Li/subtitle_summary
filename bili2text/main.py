from typing import List, Union
from pathlib import Path
from core.downloader import AudioDownloader
from core.transcriber import AudioTranscriber
from config import DEFAULT_WHISPER_MODEL, DEFAULT_PROMPT
import re


class Bili2Text:
    def __init__(self, whisper_model: str = DEFAULT_WHISPER_MODEL):
        self.downloader = AudioDownloader()
        self.transcriber = AudioTranscriber(whisper_model)

    def process_url(self, url: str, prompt: str = DEFAULT_PROMPT) -> str:
        """处理单个B站URL"""
        result = self.downloader.download_from_url(url)
        
        if result['type'] == 'subtitle':
            # 直接保存字幕文本
            bv_match = re.search(r'BV\w+', url)
            output_path = self.output_dir / f"{bv_match.group()}_subtitle.txt"
            output_path.write_text(result['subtitle_text'], encoding='utf-8')
            return str(output_path)
        elif result['type'] == 'audio':
            # 使用whisper转录音频
            return self.transcriber.transcribe_file(result['audio_path'], prompt)
        else:
            raise Exception("无法获取视频内容")

    def process_keyword(
            self,
            keyword: str,
            max_results: int = 5,
            prompt: str = DEFAULT_PROMPT
    ) -> List[str]:
        """处理关键词搜索"""
        # 下载音频
        audio_paths = self.downloader.download_from_keyword(keyword, max_results)
        if not audio_paths:
            raise Exception(f"未找到相关视频: {keyword}")

        # 转录音频
        output_paths = self.transcriber.transcribe_files(audio_paths, prompt)
        return output_paths


# 使用示例
if __name__ == "__main__":
    processor = Bili2Text(whisper_model="small")

    # 处理单个URL
    # url = "https://www.bilibili.com/video/BV1xx411c7mD"
    # result = processor.process_url(url)
    # print(f"转录完成: {result}")

    # 处理关键词搜索
    keyword = "AI咨询"
    results = processor.process_keyword(keyword, max_results=3)
    print(f"搜索并转录完成: {results}")

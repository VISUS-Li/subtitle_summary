from typing import List, Union, Dict
from services.bili2text.core.downloader import AudioDownloader
from services.bili2text.core.transcriber import AudioTranscriber
from services.bili2text.config import get_config
import re


class Bili2Text:
    def __init__(self, task_manager=None, config=None):
        self.config = config or get_config()
        self.downloader = AudioDownloader(task_manager=task_manager)
        self.transcriber = AudioTranscriber(task_manager=task_manager, config=self.config)

    def update_config(self, new_config):
        """更新配置"""
        self.config = new_config
        # 同步更新transcriber的配置
        self.transcriber.update_config(new_config)

    def process_url(self, url: str, task_id: str = None) -> Dict:
        """处理单个URL"""
        try:
            # 下载媒体
            result = self.downloader.download_media(url, task_id)
            
            if result['type'] == 'subtitle':
                return {
                    'type': 'subtitle',
                    'content': result['content']
                }
            elif result['type'] == 'audio':
                # 转录音频
                transcribed_text = self.transcriber.transcribe_file(
                    audio_path=result['content'],
                    video_id=result['video_id'],  # 使用下载器返回的video_id
                    task_id=task_id
                )
                return {
                    'type': 'whisper',
                    'content': transcribed_text
                }
                
        except Exception as e:
            if task_id and self.task_manager:
                self.task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED.value,
                    message=f"处理失败: {str(e)}"
                )
            raise

    def process_keyword(
            self,
            keyword: str,
            max_results: int = 5
    ) -> List[str]:
        """处理关键词搜索"""
        # 获取最新配置
        config = get_config()
        
        # 下载音频
        audio_paths = self.downloader.download_from_keyword(keyword, max_results)
        if not audio_paths:
            raise Exception(f"未找到相关视频: {keyword}")

        # 转录音频，使用最新配置
        output_paths = self.transcriber.transcribe_files(
            audio_paths,
            model_name=config["DEFAULT_WHISPER_MODEL"],
            language=config["DEFAULT_LANGUAGE"],
            prompt=config["DEFAULT_PROMPT"]
        )
        return output_paths


# 使用示例
# if __name__ == "__main__":
#     processor = Bili2Text()
#
#     # 处理单个URL
#     # url = "https://www.bilibili.com/video/BV1xx411c7mD"
#     # result = processor.process_url(url)
#     # print(f"转录完成: {result}")
#
#     # 处理关键词搜索
#     keyword = "AI咨询"
#     results = processor.process_keyword(keyword, max_results=3)
#     print(f"搜索并转录完成: {results}")

from typing import List, Optional
import yt_dlp
import re
from pathlib import Path
from bili2text.config import DOWNLOAD_DIR, MAX_RETRIES, RETRY_DELAY
from bili2text.core.utils import setup_logger, retry_on_failure
from bili2text.core.bilibili import BilibiliAPI

logger = setup_logger("downloader")


class AudioDownloader:
    def __init__(self):
        self.bili_api = BilibiliAPI()
        self.download_dir = DOWNLOAD_DIR

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不合法字符"""
        # 替换Windows文件系统不允许的字符
        filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
        # 替换其他可能导致问题的字符
        filename = re.sub(r'[~！@#￥%……&*（）—+=【】、；''：""，。？]', '_', filename)
        # 将多个下划线替换为单个下划线
        filename = re.sub(r'_+', '_', filename)
        # 限制文件名长度
        if len(filename) > 200:
            filename = filename[:197] + "..."
        return filename.strip('_')

    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)
    def download_from_url(self, url: str) -> Optional[str]:
        """从URL下载音频"""
        logger.info(f"开始下载音频: {url}")

        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(self.download_dir / '%(title)s-%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'restrictfilenames': True,  # 使用ASCII字符
            'windowsfilenames': True,   # 确保Windows兼容性
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # 生成安全的文件名
                safe_title = self._sanitize_filename(info['title'])
                file_path = self.download_dir / f"{safe_title}-{info['id']}.mp3"
                
                # 如果文件存在但名称不同（由于yt-dlp的文件名处理），查找实际文件
                if not file_path.exists():
                    for f in self.download_dir.glob(f"*{info['id']}.mp3"):
                        file_path = f
                        break
                
                logger.info(f"音频下载成功: {file_path}")
                return str(file_path)
        except Exception as e:
            logger.error(f"下载失败: {str(e)}")
            raise

    def download_from_keyword(self, keyword: str, max_results: int = 5) -> List[str]:
        """通过关键词搜索并下载音频"""
        logger.info(f"开始搜索关键词: {keyword}, 最大结果数: {max_results}")

        downloaded_files = []
        videos = self.bili_api.search_videos(keyword, max_results)

        for video in videos:
            try:
                url = f"https://www.bilibili.com/video/{video['bvid']}"
                file_path = self.download_from_url(url)
                if file_path:
                    downloaded_files.append(file_path)
            except Exception as e:
                logger.error(f"下载视频失败 {video['bvid']}: {str(e)}")
                continue

        return downloaded_files

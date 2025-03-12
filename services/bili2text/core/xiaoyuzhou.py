import os
import sys
import requests
import random
import time
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, Optional, List
from services.config_service import ConfigurationService
from db.models.subtitle import Platform, SubtitleSource
from services.bili2text.core.transcriber import AudioTranscriber
from services.bili2text.core.subtitle_manager import SubtitleManager
from services.bili2text.core.utils import retry_on_failure


class XiaoyuzhouAPI:
    """小宇宙播客API封装"""

    def __init__(self):
        """初始化小宇宙API"""
        self.config_service = ConfigurationService()
        self.subtitle_manager = SubtitleManager()
        self.transcriber = AudioTranscriber()
        
        # 获取输出目录配置
        self.output_dir = Path(self.config_service.get_config("system", "output_dir"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.last_request_time = 0
        self.request_interval = random.uniform(2, 5)  # 请求间隔2-5秒
        self.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.xiaoyuzhoufm.com/',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
    }

    def get_video_info(self, video_id: str) -> dict:
        """获取播客信息
        
        Args:
            video_id: 播客ID
            
        Returns:
            dict: 播客信息字典
        """
        try:
            url = f"https://www.xiaoyuzhoufm.com/episode/{video_id}"
            episode_info = self._extract_episode_info(url)
            
            return {
                'id': episode_info['id'],
                'title': episode_info['title'],
                'description': episode_info['description'],
                'url': episode_info['page_url'],
                'audio_url': episode_info['audio_url']
            }
        except Exception as e:
            error_msg = f"获取播客信息失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def get_subtitle(self, video_id: str) -> Optional[str]:
        """获取播客字幕（小宇宙无官方字幕，返回None）
        
        Args:
            video_id: 播客ID
            
        Returns:
            Optional[str]: 字幕内容，小宇宙始终返回None
        """
        return None  # 小宇宙没有官方字幕

    @retry_on_failure(max_retries=3)
    def search_videos(self, keyword: str, max_results: int = 20) -> List[Dict]:
        """搜索播客
        
        Args:
            keyword: 搜索关键词
            max_results: 最大结果数量
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            print(f"搜索小宇宙播客: {keyword}")
            # 这里实现搜索功能，目前返回空列表因为小宇宙没有开放搜索API
            # 如果后续有搜索API，在这里实现
            return []
        except Exception as e:
            error_msg = f"搜索播客失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    @retry_on_failure(max_retries=3)
    def download_audio(self, url: str, output_path: str) -> str:
        """下载音频
        
        Args:
            url: 播客URL
            output_path: 输出文件路径
            
        Returns:
            str: 下载的音频文件路径
        """
        try:
            # 获取播客信息
            episode_info = self._extract_episode_info(url)
            # 下载音频文件
            audio_path = self._download_audio(episode_info['audio_url'], episode_info['id'])
            
            # 如果下载路径与期望路径不同，进行移动
            if audio_path != output_path and os.path.exists(audio_path):
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(audio_path, output_path)
                audio_path = output_path
                
            return audio_path
            
        except Exception as e:
            error_msg = f"下载播客音频失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def _wait_for_next_request(self):
        """控制请求频率"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.request_interval:
            sleep_time = self.request_interval - time_since_last_request
            print(f"等待 {sleep_time:.1f} 秒以控制请求频率...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()


    def _extract_episode_info(self, url: str) -> Dict:
        """从播客页面提取信息"""
        try:
            self._wait_for_next_request()
                        
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取音频URL
            audio_meta = soup.find("meta", {"property": "og:audio"})
            if not audio_meta or not audio_meta.get("content"):
                raise ValueError("未找到音频URL")
            
            # 提取标题
            title_meta = soup.find("meta", {"property": "og:title"})
            title = title_meta.get("content") if title_meta else "未知标题"
            
            # 提取描述
            desc_meta = soup.find("meta", {"property": "og:description"})
            description = desc_meta.get("content") if desc_meta else ""
            
            # 提取episode ID
            episode_id = url.split("/")[-1]
            
            return {
                "id": episode_id,
                "title": title,
                "description": description,
                "audio_url": audio_meta["content"],
                "page_url": url
            }
        except Exception as e:
            error_msg = f"提取播客信息失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def _download_audio(self, audio_url: str, episode_id: str) -> str:
        """下载音频文件"""
        try:
            self._wait_for_next_request()
            # 构建输出文件路径
            output_path = self.output_dir / f"xiaoyuzhou_{episode_id}.mp3"
            
            # 下载音频文件
            response = requests.get(audio_url,headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 保存音频文件
            with open(output_path, "wb") as f:
                f.write(response.content)
                
            return str(output_path)
            
        except Exception as e:
            error_msg = f"下载音频失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    async def process_episode(self, url: str, topic: str = "podcast") -> Optional[Dict]:
        """处理小宇宙播客单集
        
        Args:
            url: 播客集数URL
            topic: 主题标签
            
        Returns:
            Optional[Dict]: 处理结果
        """
        try:
            # 1. 提取播客信息
            print(f"正在处理播客: {url}")
            episode_info = self._extract_episode_info(url)
            episode_id = episode_info["id"]
            
            # 2. 检查是否已存在字幕
            existing_subtitle = self.subtitle_manager.get_subtitle(episode_id)
            if existing_subtitle:
                print(f"找到现有字幕: {episode_id}")
                return {
                    'type': 'subtitle',
                    'content': existing_subtitle['content'],
                    'video_id': episode_id
                }
            
            # 3. 下载音频
            print("开始下载音频...")
            audio_path = self._download_audio(episode_info["audio_url"], episode_id)
            
            # 4. 使用Whisper转录
            print("开始转录音频...")
            content = await self.transcriber.transcribe_file(
                topic=topic,
                audio_path=audio_path,
                video_id=episode_id,
                platform=Platform.XIAOYUZHOU
            )
            
            # 5. 保存视频信息
            self.subtitle_manager.save_video_info(
                video_id=episode_id,
                platform=Platform.XIAOYUZHOU,
                title=episode_info["title"],
                description=episode_info["description"],
                url=episode_info["page_url"]
            )
            
            # 6. 删除临时音频文件
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return {
                'type': 'subtitle',
                'content': content,
                'video_id': episode_id,
                'title': episode_info["title"]
            }
            
        except Exception as e:
            error_msg = f"处理播客失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise
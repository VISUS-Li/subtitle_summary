import os
import random
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
from db.models.subtitle import SubtitleSource, Platform
from services.bili2text.core.subtitle_manager import SubtitleManager
from services.bili2text.core.utils import retry_on_failure
from services.config_service import ConfigurationService


class AudioDownloader:
    """音频下载器,负责从各平台下载音频"""

    def __init__(self, config_path: str = "config.yaml"):
        """初始化音频下载器
        
        Args:
            config_path: 配置文件路径，默认为 config.yaml
        """
        config_service = ConfigurationService()
        self.download_dir = Path(config_service.get_config("system", "download_dir"))
        self._bili_api = None
        self._youtube_api = None
        self._subtitle_manager = None
        self._xiaoyuzhou_api = None  # 添加小宇宙API实例
        self.config_path = config_path
        self.last_api_request_time = 0  # 记录上次请求API的时间

        # 确保下载目录存在
        self.download_dir.mkdir(parents=True, exist_ok=True)

    @property
    def bili_api(self):
        if self._bili_api is None:
            start_time = time.time()
            print(f"[{time.time()}] 开始导入并初始化B站API...")
            from services.bili2text.core.bilibili import BilibiliAPI
            self._bili_api = BilibiliAPI()
            print(f"[{time.time()}] B站API初始化完成，耗时: {time.time() - start_time:.2f}秒")
        return self._bili_api

    @property
    def youtube_api(self):
        if self._youtube_api is None:
            start_time = time.time()
            print(f"[{time.time()}] 开始导入并初始化YouTube API...")
            from services.bili2text.core.youtube import YoutubeAPI
            self._youtube_api = YoutubeAPI()
            print(f"[{time.time()}] YouTube API初始化完成，耗时: {time.time() - start_time:.2f}秒")
        return self._youtube_api

    @property
    def xiaoyuzhou_api(self):
        """获取小宇宙API实例"""
        if self._xiaoyuzhou_api is None:
            start_time = time.time()
            print(f"[{time.time()}] 开始导入并初始化小宇宙API...")
            from services.bili2text.core.xiaoyuzhou import XiaoyuzhouAPI
            self._xiaoyuzhou_api = XiaoyuzhouAPI()
            print(f"[{time.time()}] 小宇宙API初始化完成，耗时: {time.time() - start_time:.2f}秒")
        return self._xiaoyuzhou_api

    @property
    def subtitle_manager(self):
        if self._subtitle_manager is None:
            self._subtitle_manager = SubtitleManager(self.config_path)
        return self._subtitle_manager

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名,移除不合法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 清理后的文件名
        """
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

    def _get_existing_file(self, video_id: str) -> Optional[Path]:
        """检查是否存在已下载的文件
        
        Args:
            video_id: 视频ID
            
        Returns:
            Optional[Path]: 文件路径,不存在则返回None
        """
        existing_files = list(self.download_dir.glob(f"*{video_id}.mp3"))
        if existing_files:
            return existing_files[0]
        return None

    def _extract_video_id(self, url: str) -> str:
        """从URL中提取视频/播客ID
        
        Args:
            url: 视频URL
            
        Returns:
            str: 视频ID
            
        Raises:
            ValueError: URL格式无效
        """
        if 'xiaoyuzhoufm.com' in url.lower():
            # 处理小宇宙URL
            return url.split('/')[-1]
        if 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
            if 'youtu.be' in url:
                return url.split('/')[-1]
            else:
                pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
                match = re.search(pattern, url)
                if not match:
                    raise ValueError("无效的YouTube URL")
                return match.group(1)
        else:
            bv_match = re.search(r'BV\w+', url)
            if not bv_match:
                raise ValueError("无效的B站URL:" + url)
            return bv_match.group()

    def _verify_downloaded_file(self, file_path: str) -> bool:
        """验证下载的文件是否有效
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否有效
        """
        # 获取不带扩展名的文件路径
        file_base = os.path.splitext(file_path)[0]

        # 检查目录下是否存在以该基础名开头的其他文件
        dir_path = os.path.dirname(file_path)
        base_name = os.path.basename(file_base)

        # for f in os.listdir(dir_path):
        #     if f.startswith(base_name):
        #         full_path = os.path.join(dir_path, f)
        #         if full_path != file_path:  # 如果不是目标mp3文件
        #             print(f"发现同名临时文件: {f}")
        #             os.remove(full_path)  # 删除临时文件

        # 检查目标mp3文件
        if not os.path.exists(file_path):
            return False
        if os.path.getsize(file_path) == 0:
            # 删除空文件
            os.remove(file_path)
            return False

        return True

    @retry_on_failure()
    async def download_media(self, topic: str, url: str) -> Dict:
        """下载媒体文件
        
        Args:
            url: 视频URL
            
        Returns:
            Dict: 下载结果,包含:
                - type: 'subtitle' 或 'audio'
                - content: 字幕内容或音频文件路径
                - video_id: 视频ID
                - platform: 平台
                
        Raises:
            Exception: 下载失败
        """
        try:
            print(f"开始下载媒体: {url}")
            video_id = self._extract_video_id(url)
            
            # 确定平台
            if 'youtube' in url.lower():
                platform = Platform.YOUTUBE
            elif 'bilibili' in url.lower():
                platform = Platform.BILIBILI
            elif 'xiaoyuzhoufm.com' in url.lower():
                platform = Platform.XIAOYUZHOU
            else:
                raise ValueError("不支持的平台")

            # 获取视频信息以显示标题
            video_info = self.subtitle_manager.get_video_info(platform, video_id)
            if video_info:
                video_title = f"「{video_info['title']}」" if video_info.get('title') else ''
                print(f"数据库中已存在视频信息 [{platform.value}] {video_id} {video_title}")

            # 1. 检查数据库中是否存在字幕
            existing_subtitle = self.subtitle_manager.get_subtitle(video_id)
            if existing_subtitle:
                print(f"找到现有字幕 [{platform.value}] {video_id} {video_title if video_info else ''}")
                return {
                    'type': 'subtitle',
                    'content': existing_subtitle['content'],
                    'video_id': video_id,
                    'platform': platform
                }

            # 2. 根据平台选择API并检查请求频率
            api = self.youtube_api if platform == Platform.YOUTUBE else self.bili_api if platform == Platform.BILIBILI else self.xiaoyuzhou_api

            # 对B站API请求进行频率控制
            if platform == Platform.BILIBILI:
                current_time = time.time()
                time_since_last_request = current_time - self.last_api_request_time
                delay = random.uniform(10, 20)  # 10-20秒随机延迟
                if time_since_last_request < delay:  # 假设需要10秒间隔
                    delay = delay - time_since_last_request
                    print(f"等待 {delay:.1f} 秒以控制请求频率...")
                    time.sleep(delay)
                self.last_api_request_time = time.time()

            # 3. 获取视频信息
            print(f"请求视频信息 [{platform.value}] {video_id} {video_title if video_info else ''}...")
            api_video_info = api.get_video_info(video_id)

            # 4. 尝试获取官方字幕
            print("尝试获取官方字幕...")
            subtitle_text = api.get_subtitle(video_id)
            if subtitle_text:
                print("找到官方字幕,保存中...")
                self.subtitle_manager.save_video_info(api_video_info, platform)
                try:
                    await self.subtitle_manager.save_subtitle(
                        topic=topic,
                        video_id=video_id,
                        content=subtitle_text,
                        timed_content=None,
                        source=SubtitleSource.OFFICIAL,
                        platform=platform,
                        platform_vid=video_id,
                        language='zh'
                    )
                except Exception as e:
                    print(f"保存字幕失败: {str(e)}")
                    raise
                return {
                    'type': 'subtitle',
                    'content': subtitle_text,
                    'video_id': video_id,
                    'platform': platform
                }

            # 5. 未找到字幕,下载音频
            print("未找到官方字幕,准备下载音频...")

            # 检查是否有现成的音频文件
            video_info = self.subtitle_manager.get_video_info(platform, video_id)
            if video_info and video_info['audio_path']:
                audio_path = video_info['audio_path']
                if Path(audio_path).exists():
                    print(f"找到现有音频文件: {audio_path}")
                    return {
                        'type': 'audio',
                        'content': audio_path,
                        'video_id': video_id,
                        'platform': platform
                    }

            # 下载新的音频文件
            audio_path = str(self.download_dir / f'{video_id}.mp3')
            # 先检查并删除可能存在的同名文件
            if os.path.exists(audio_path):
                os.remove(audio_path)

            try:
                if platform == Platform.XIAOYUZHOU:
                    # 使用小宇宙API处理
                    episode_info = self.xiaoyuzhou_api._extract_episode_info(url)
                    audio_path = self.xiaoyuzhou_api._download_audio(
                        episode_info["audio_url"], 
                        video_id
                    )
                    
                    # 保存视频信息
                    self.subtitle_manager.save_video_info(
                        {
                            'id': video_id,
                            'title': episode_info['title'],
                            'description': episode_info['description'],
                            'url': url
                        },
                        platform,
                        audio_path=audio_path
                    )
                    
                    return {
                        'type': 'audio',
                        'content': audio_path,
                        'video_id': video_id,
                        'platform': platform,
                        'title': episode_info['title']
                    }
                else:
                    # 现有的B站和YouTube处理逻辑
                    audio_path = api.download_audio(url, audio_path)
                    # 验证下载的文件
                    if not self._verify_downloaded_file(audio_path):
                        raise Exception("下载完成但文件无效")

                    print(f"音频下载完成: {audio_path}")

                    # 保存视频信息
                    print("保存视频信息...")
                    self.subtitle_manager.save_video_info(
                        api_video_info,
                        platform,
                        audio_path=audio_path
                    )

                    return {
                        'type': 'audio',
                        'content': audio_path,
                        'video_id': video_id,
                        'platform': platform
                    }

            except Exception as e:
                # 如果下载失败，清理可能存在的不完整文件
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                raise Exception(f"音频下载失败: {str(e)}")

        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    async def search_videos(self, keyword: str, platform: Platform, max_results: int = 200) -> List[Dict]:
        """搜索视频
        
        Args:
            keyword: 搜索关键词
            platform: 平台 (BILIBILI 或 YOUTUBE)
            max_results: 最大结果数量
            
        Returns:
            List[Dict]: 搜索结果列表
            
        Raises:
            ValueError: 平台不支持
            Exception: 搜索失败
        """
        try:
            print(f"在{platform.value}上搜索视频: {keyword}")

            if platform == Platform.YOUTUBE:
                if not self.youtube_api:
                    raise ValueError("YouTube API未初始化")
                return self.youtube_api.search_videos(keyword, max_results)

            elif platform == Platform.BILIBILI:
                if not self.bili_api:
                    raise ValueError("B站API未初始化")
                return await self.bili_api.search_videos(keyword, max_results)

            else:
                raise ValueError(f"不支持的平台: {platform}")

        except Exception as e:
            error_msg = f"搜索视频失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

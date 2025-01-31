import asyncio
import random
import sys
from typing import Dict, List

from db.models.subtitle import Platform
from services.bili2text.core.downloader import AudioDownloader
from services.bili2text.core.subtitle_manager import SubtitleManager
from services.bili2text.core.transcriber import AudioTranscriber


class VideoProcessor:
    """视频处理核心类,负责视频下载、转写等业务逻辑"""
    
    def __init__(self, downloader: AudioDownloader, transcriber: AudioTranscriber):
        self.downloader = downloader
        self.transcriber = transcriber
        self.subtitle_manager = SubtitleManager()

    async def process_single_video(self, video_id: str, platform: Platform) -> Dict:
        """处理单个视频
        
        Args:
            video_id: 视频ID
            platform: 平台(YOUTUBE/BILIBILI)
            task_id: 任务ID(可选)
            
        Returns:
            Dict: 处理结果
        """
        try:
            print(f"开始处理视频: {video_id}")
            
            # 1. 检查是否已存在字幕
            existing_subtitle = self.subtitle_manager.get_subtitle(video_id)
            if existing_subtitle:
                print(f"找到现有字幕: {video_id}")
                return {
                    'type': 'subtitle',
                    'content': existing_subtitle['content'],
                    'video_id': video_id
                }
            
            # 2. 获取视频信息并尝试获取官方字幕
            print("获取视频信息...")
            video_url = self._get_video_url(video_id, platform)
            result = await self._download_and_process(video_url, platform)
            
            # 3. 获取视频标题等信息用于显示
            video_info = self.subtitle_manager.get_video_info(platform, video_id)
            if video_info:
                result['title'] = video_info.get('title', '')
                
            print(f"视频处理完成: {video_id}")
            return result
            
        except Exception as e:
            error_msg = f"处理视频失败 {video_id}: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    async def process_batch_videos(self, keyword: str, platform: Platform, max_results: int, task_id: str = None) -> List[Dict]:
        """批量处理视频
        
        Args:
            keyword: 搜索关键词
            platform: 平台
            max_results: 最大结果数
            task_id: 任务ID(可选)
            
        Returns:
            List[Dict]: 处理结果列表
        """
        try:
            print(f"开始批量处理关键词: {keyword}, 最大结果数: {max_results}")
            
            # 1. 搜索视频
            videos = await asyncio.to_thread(
                self.downloader.search_videos,
                keyword,
                platform,
                max_results
            )
            
            results = []
            total = len(videos)
            
            # 2. 逐个处理视频
            for i, video in enumerate(videos, 1):
                video_id = video['id']
                try:
                    print(f"处理第 {i}/{total} 个视频: {video_id}")
                    
                    # 处理单个视频
                    result = await self.process_single_video(video_id, platform)
                    
                    # 更新搜索相关信息
                    self.subtitle_manager.update_video_search_info(
                        video_id,
                        keyword,
                        i,
                        'search'
                    )
                    
                    results.append(result)
                    print(f"进度: {i}/{total}")
                    
                    # 添加间隔,避免请求过于频繁
                    delay = random.uniform(10, 20)  # 10-20秒随机延迟
                    print(f"等待 {delay:.1f} 秒后继续下一个视频")
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    print(f"处理视频失败 {video_id}: {str(e)}")
                    continue
                    
            print(f"批量处理完成, 成功处理 {len(results)}/{total} 个视频")
            return results
            
        except Exception as e:
            error_msg = f"批量处理失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    async def _download_and_process(self, url: str, platform: Platform) -> Dict:
        """下载并处理视频
        
        Args:
            url: 视频URL
            platform: 平台
            task_id: 任务ID
            
        Returns:
            Dict: 处理结果
        """
        try:
            print(f"开始下载处理: {url}")
            
            # 1. 下载媒体
            result = await asyncio.to_thread(
                self.downloader.download_media,
                url
            )
            
            # 2. 如果是字幕,直接返回
            if result['type'] == 'subtitle':
                print("获取到字幕,处理完成")
                return result
                
            # 3. 如果是音频,进行转写
            elif result['type'] == 'audio':
                print("开始音频转写...")
                text = await asyncio.to_thread(
                    self.transcriber.transcribe_file,
                    result['content'],
                    result['video_id'],
                    platform
                )
                print("音频转写完成")
                
                return {
                    'type': 'audio',
                    'content': text,
                    'video_id': result['video_id']
                }
                
        except Exception as e:
            error_msg = f"下载处理失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def _get_video_url(self, video_id: str, platform: Platform) -> str:
        """根据平台生成视频URL"""
        if platform == Platform.YOUTUBE:
            return f"https://www.youtube.com/watch?v={video_id}"
        elif platform == Platform.BILIBILI:
            return f"https://www.bilibili.com/video/{video_id}"
        else:
            raise ValueError(f"不支持的平台: {platform}") 
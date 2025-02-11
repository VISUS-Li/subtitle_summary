import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Union
import re
import asyncio

from db.init.base import get_db
from db.models.subtitle import Video, Subtitle, SubtitleSource, Platform, SubtitleSummary, GeneratedScript, TaskStatus
from services.coze.coze import CozeClient
from services.coze.config import CozeConfig, Config
from db.models.subtitle import get_video_url


class SubtitleManager:
    """字幕管理类，负责字幕和视频信息的数据库操作"""

    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化字幕管理器
        
        Args:
            config_path: 配置文件路径，默认为 config.yaml
        """
        try:
            # 从配置文件加载配置
            config = Config.from_yaml(config_path)
            self.coze_client = CozeClient(config.coze)
        except Exception as e:
            raise Exception(f"初始化 SubtitleManager 失败: {str(e)}")

    @contextmanager
    def _db_transaction(self):
        """数据库事务上下文管理器"""
        with get_db() as db:
            try:
                yield db
                db.commit()
            except Exception as e:
                db.rollback()
                raise

    def get_video_info(self, platform, platform_vid: str) -> Optional[Dict]:
        """获取视频信息"""
        with get_db() as db:
            video = db.query(Video).filter(
                Video.platform == platform,
                Video.platform_vid == platform_vid
            ).first()
            if video:
                return {
                    'id': video.id,
                    'platform': video.platform.value,
                    'title': video.title,
                    'author': video.author,
                    'duration': video.duration,
                    'view_count': video.view_count,
                    'tags': video.tags,
                    'keywords': video.keywords,
                    'description': video.description,
                    'audio_path': video.audio_path,
                    'create_time': video.create_time.isoformat() if video.create_time else None,
                    'update_time': video.update_time.isoformat() if video.update_time else None
                }
        return None

    def save_video_info(
        self, 
        video_info: Dict, 
        platform: Platform,
        audio_path: Optional[str] = None
    ) -> str:
        """保存视频信息，返回内部video_id"""
        try:
            print(f"开始保存视频信息: {video_info.get('id')}")
            with self._db_transaction() as db:
                platform_vid = video_info.get('id')
                
                video = db.query(Video).filter(
                    Video.platform == platform,
                    Video.platform_vid == platform_vid
                ).first()
                
                if not video:
                    print("创建新的视频记录...")
                    video_id = str(uuid.uuid4())
                    video = Video(
                        id=video_id,
                        platform=platform,
                        platform_vid=platform_vid,
                        title=video_info.get('title'),
                        author=video_info.get('author'),
                        duration=video_info.get('duration'),
                        view_count=video_info.get('view_count'),
                        tags=video_info.get('tags', []),
                        keywords=video_info.get('keywords', []),
                        description=video_info.get('description'),
                        audio_path=audio_path
                    )
                    
                    # 设置平台特定信息
                    if platform == Platform.BILIBILI:
                        video.bilibili_aid = video_info.get('aid')
                        video.bilibili_cid = video_info.get('cid')
                    elif platform == Platform.YOUTUBE:
                        video.youtube_channel_id = video_info.get('channel_id')
                        video.youtube_playlist_id = video_info.get('playlist_id')
                    
                    db.add(video)
                    print(f"新视频记录已创建: {video_id}")
                else:
                    video_id = video.id
                    print(f"更新现有视频记录: {video_id}")
                    video.update_time = datetime.utcnow()
                    if audio_path:
                        video.audio_path = audio_path
                
                return video_id
                
        except Exception as e:
            error_msg = f"保存视频信息失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def get_platform_video_id(self, internal_id: str) -> Optional[Dict]:
        """根据内部ID获取平台视频ID信息"""
        with get_db() as db:
            video = db.query(Video).get(internal_id)
            if video:
                result = {
                    'platform': video.platform.value,
                    'platform_vid': video.platform_vid,
                }
                if video.platform == Platform.BILIBILI:
                    result.update({
                        'aid': video.bilibili_aid,
                        'cid': video.bilibili_cid
                    })
                elif video.platform == Platform.YOUTUBE:
                    result.update({
                        'channel_id': video.youtube_channel_id,
                        'playlist_id': video.youtube_playlist_id
                    })
                return result
        return None

    async def save_subtitle(
        self,
        topic: str,
        video_id: str,
        content: Union[str, Dict],  # 可以接收字符串或字典格式的内容
        timed_content,
        source: SubtitleSource,
        platform: Platform,
        platform_vid: str,
        language: str = 'zh',
        model_name: Optional[str] = None
    ) -> None:
        """保存字幕信息
        
        Args:
            video_id: 视频ID
            content: 字幕内容，可以是:
                - 纯文本字符串
                - Whisper格式的字典 {'text': str, 'segments': List[Dict]}
                - yt-dlp格式的字典或WebVTT格式的字符串
            source: 字幕来源
            platform: 视频平台
            platform_vid: 平台视频ID
            language: 字幕语言
            model_name: Whisper模型名称
        """
        try:
            with self._db_transaction() as db:
                # 检查视频是否存在
                video = db.query(Video).filter(
                    Video.platform == platform,
                    Video.platform_vid == platform_vid
                ).first()
                
                if not video:
                    # 如果视频不存在，创建新的视频记录
                    raise ValueError(f"视频不存在: {video_id}")
                
                # 处理字幕内容
                pure_text = ""
                detected_language = language  # 默认使用传入的语言
                
                if isinstance(content, str):
                    if "WEBVTT" in content or "-->" in content:
                        # 清理XML标签和时间戳标签
                        lines = content.split('\n')
                        cleaned_lines = []
                        
                        for line in lines:
                            if not line.strip().startswith('WEBVTT') and \
                               not line.strip().startswith('Kind:') and \
                               not line.strip().startswith('Language:') and \
                               not '-->' in line and \
                               not line.strip().isdigit():
                                # 首先移除时间戳标签
                                cleaned_text = re.sub(r'<\d+:\d+:\d+\.\d+>', '', line)
                                # 然后移除其他XML标签
                                cleaned_text = re.sub(r'<[^>]+>', '', cleaned_text)
                                # 移除多余的空格
                                cleaned_text = ' '.join(cleaned_text.split())
                                if cleaned_text:
                                    cleaned_lines.append(cleaned_text)
                                    
                        pure_text = ' '.join(cleaned_lines)
                        
                        # 只在timed_content为None时处理时间戳内容
                        if timed_content is None:
                            metadata = {}
                            segments = []
                            current_text = []
                            current_time = None
                            
                            # 解析WebVTT头部信息
                            for line in lines:
                                line = line.strip()
                                if line.startswith('Kind:'):
                                    metadata['kind'] = line.split(':', 1)[1].strip()
                                elif line.startswith('Language:'):
                                    lang = line.split(':', 1)[1].strip()
                                    detected_language = lang.split('-')[0].lower()
                                    metadata['language'] = lang
                                elif '-->' in line:
                                    break
                            
                            # 解析分段
                            for line in lines:
                                line = line.strip()
                                if '-->' in line:
                                    if current_time and current_text:
                                        segments.append({
                                            'start': current_time['start'],
                                            'end': current_time['end'],
                                            'text': ' '.join(current_text)
                                        })
                                        current_text = []
                                    
                                    time_parts = line.split('-->')
                                    start_time = self._parse_timestamp(time_parts[0].strip())
                                    end_time = self._parse_timestamp(time_parts[1].strip())
                                    current_time = {'start': start_time, 'end': end_time}
                                    
                                elif line and not line.startswith('WEBVTT') and \
                                     not line.startswith('Kind:') and \
                                     not line.startswith('Language:') and \
                                     not line[0].isdigit() and \
                                     current_time is not None:
                                    cleaned_text = re.sub(r'<[^>]+>', '', line)
                                    cleaned_text = ' '.join(cleaned_text.split())
                                    if cleaned_text:
                                        current_text.append(cleaned_text)
                            
                            if current_time and current_text:
                                segments.append({
                                    'start': current_time['start'],
                                    'end': current_time['end'],
                                    'text': ' '.join(current_text)
                                })
                            
                            timed_content = {
                                'type': 'webvtt',
                                'metadata': metadata,
                                'segments': segments
                            }
                    else:
                        pure_text = content
                        
                elif isinstance(content, dict):
                    if 'text' in content:
                        pure_text = content['text']
                        if timed_content is None and 'segments' in content:
                            timed_content = {
                                'type': 'whisper',
                                'segments': [
                                    {
                                        'start': seg['start'],
                                        'end': seg['end'],
                                        'text': seg['text']
                                    }
                                    for seg in content['segments']
                                ]
                            }
                    else:
                        texts = []
                        for value in content.values():
                            texts.append(value)
                        pure_text = ' '.join(texts)
                        
                        if timed_content is None:
                            segments = []
                            for key, value in content.items():
                                if isinstance(key, (int, float)):
                                    start_time = float(key)
                                else:
                                    start_time = self._parse_timestamp(key)
                                
                                segments.append({
                                    'start': start_time,
                                    'text': value
                                })
                            
                            timed_content = {
                                'type': 'yt-dlp',
                                'segments': sorted(segments, key=lambda x: x['start'])
                            }
                
                # 创建字幕记录
                subtitle = Subtitle(
                    video_id=video.id,
                    platform_vid=video.platform_vid,
                    platform=platform,
                    source=source,
                    content=pure_text,
                    timed_content=timed_content,
                    language=detected_language,
                    model_name=model_name
                )
                db.add(subtitle)
                db.flush()  # 确保获取到subtitle.id
                
        except Exception as e:
            print(f"保存字幕失败: {str(e)}")
            raise

    def _parse_timestamp(self, timestamp: str) -> float:
        """解析时间戳字符串为秒数
        
        支持格式:
        - HH:MM:SS.mmm
        - MM:SS.mmm
        - SS.mmm
        """
        try:
            # 移除可能存在的毫秒以外的小数点
            parts = timestamp.replace(',', '.').split(':')
            
            if len(parts) == 3:  # HH:MM:SS.mmm
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:  # MM:SS.mmm
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:  # SS.mmm
                return float(parts[0])
        except (ValueError, IndexError):
            raise ValueError(f"无效的时间戳格式: {timestamp}")

    def get_subtitle(self, video_id: str, with_timestamps: bool = False) -> Optional[Dict]:
        """获取字幕内容
        
        Args:
            video_id: 视频ID
            with_timestamps: 是否返回带时间戳的内容
            
        Returns:
            Dict: 字幕信息字典
        """
        try:
            with self._db_transaction() as db:
                subtitle = db.query(Subtitle).join(Video).filter(
                    Video.platform_vid == video_id
                ).first()
                
                if subtitle:
                    result = {
                        'id': subtitle.id,
                        'content': subtitle.content,
                        'source': subtitle.source.value,
                        'language': subtitle.language,
                        'model_name': subtitle.model_name,
                        'create_time': subtitle.create_time.isoformat() if subtitle.create_time else None
                    }
                    
                    if with_timestamps and subtitle.timed_content:
                        result['timed_content'] = subtitle.timed_content
                        
                    return result
                    
            return None
            
        except Exception as e:
            print(f"获取字幕失败: {str(e)}")
            raise
        
    def search_videos_by_tags(self, tags: List[str]) -> List[Dict]:
        """通过标签搜索视频"""
        with get_db() as db:
            videos = db.query(Video).filter(
                Video.tags.contains(tags)
            ).all()
            return [
                {
                    'id': v.id,
                    'title': v.title,
                    'platform': v.platform.value,
                    'subtitle': self.get_subtitle(v.id)
                }
                for v in videos
            ] 

    def clean_old_audio_files(self, max_age_days: int = 7):
        """清理过期的音频文件"""
        with get_db() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            old_videos = db.query(Video).filter(
                Video.update_time < cutoff_date,
                Video.audio_path.isnot(None)
            ).all()
            
            for video in old_videos:
                if video.audio_path and os.path.exists(video.audio_path):
                    try:
                        os.remove(video.audio_path)
                        video.audio_path = None
                        db.commit()
                    except Exception as e:
                        print(f"清理音频文件失败 {video.audio_path}: {str(e)}")

    def get_video_by_platform_id(self, platform: Platform, platform_vid: str) -> Optional[Dict]:
        """通过平台视频ID获取视频信息
        
        Args:
            platform: 平台类型 (Platform.BILIBILI 或 Platform.YOUTUBE)
            platform_vid: 平台视频ID (B站bvid或YouTube视频ID)
            
        Returns:
            Dict: 视频信息字典，若未找到则返回None
        """
        with get_db() as db:
            video = db.query(Video).filter(
                Video.platform == platform,
                Video.platform_vid == platform_vid
            ).first()
            
            if video:
                result = {
                    'id': video.id,
                    'platform': video.platform.value,
                    'platform_vid': video.platform_vid,
                    'title': video.title,
                    'author': video.author,
                    'duration': video.duration,
                    'view_count': video.view_count,
                    'tags': video.tags,
                    'keywords': video.keywords,
                    'description': video.description,
                    'audio_path': video.audio_path,
                    'create_time': video.create_time.isoformat() if video.create_time else None,
                    'update_time': video.update_time.isoformat() if video.update_time else None
                }
                
                # 添加平台特定信息
                if platform == Platform.BILIBILI:
                    result.update({
                        'aid': video.bilibili_aid,
                        'cid': video.bilibili_cid
                    })
                elif platform == Platform.YOUTUBE:
                    result.update({
                        'channel_id': video.youtube_channel_id,
                        'playlist_id': video.youtube_playlist_id
                    })
                    
                return result
        return None 

    def update_video_search_info(
        self,
        platform_vid: str,
        search_keyword: str,
        search_rank: int,
        source_type: str = 'search'
    ) -> None:
        """更新视频搜索相关信息"""
        try:
            with self._db_transaction() as db:
                video = db.query(Video).filter(
                    Video.platform_vid == platform_vid
                ).first()
                
                if video:
                    video.source_type = source_type
                    video.search_keyword = search_keyword
                    video.search_rank = search_rank
                    video.update_time = datetime.utcnow()
                    print(f"更新视频搜索信息成功: {platform_vid}")
                else:
                    print(f"未找到视频记录: {platform_vid}")
                    
        except Exception as e:
            print(f"更新视频搜索信息失败: {str(e)}")
            raise 

    def get_subtitle_summary(self, subtitle_id: int) -> Optional[Dict]:
        """获取字幕总结"""
        try:
            with get_db() as db:
                summary = db.query(SubtitleSummary).filter(
                    SubtitleSummary.subtitle_id == subtitle_id
                ).first()
                
                if summary:
                    return {
                        'content': summary.content,
                        'create_time': summary.create_time.isoformat() if summary.create_time else None,
                        'update_time': summary.update_time.isoformat() if summary.update_time else None
                    }
                return None
        except Exception as e:
            print(f"获取字幕总结失败: {str(e)}")
            raise

    def save_subtitle_summary(self, subtitle_id: int, content: str) -> None:
        """保存字幕总结"""
        try:
            with self._db_transaction() as db:
                summary = SubtitleSummary(
                    subtitle_id=subtitle_id,
                    content=content
                )
                db.add(summary)
                print(f"字幕总结保存成功: subtitle_id={subtitle_id}")
        except Exception as e:
            print(f"保存字幕总结失败: {str(e)}")
            raise 

    def get_videos_with_subtitles_and_summaries(
        self,
        platform: Platform,
        search_keyword: str
    ) -> List[Dict]:
        """获取指定平台和关键词的所有视频信息，包括字幕和总结
        
        Args:
            platform: 平台
            search_keyword: 搜索关键词
            
        Returns:
            List[Dict]: 视频信息列表
        """
        try:
            with get_db() as db:
                # 联合查询视频、字幕和总结信息
                query = (
                    db.query(Video, Subtitle, SubtitleSummary)
                    .join(Subtitle, Video.id == Subtitle.video_id)
                    .outerjoin(SubtitleSummary, Subtitle.id == SubtitleSummary.subtitle_id)
                    .filter(
                        Video.platform == platform,
                        Video.search_keyword == search_keyword
                    )
                    .order_by(Video.search_rank)
                )
                
                results = []
                for video, subtitle, summary in query.all():
                    video_data = {
                        'id': video.id,
                        'platform': video.platform.value,
                        'platform_vid': video.platform_vid,
                        'title': video.title,
                        'author': video.author,
                        'search_rank': video.search_rank,
                        'subtitle': {
                            'id': subtitle.id,
                            'content': subtitle.content,
                            'language': subtitle.language,
                            'source': subtitle.source.value
                        } if subtitle else None,
                        'point_summary': {
                            'content': summary.content,
                            'create_time': summary.create_time.isoformat() if summary.create_time else None
                        } if summary else None
                    }
                    results.append(video_data)
                
                return results
                
        except Exception as e:
            print(f"获取视频信息失败: {str(e)}")
            raise

    def save_generated_script(
        self,
        topic: str,
        platform: Platform,
        content: str,
        video_count: int,
        videos_data: List[Dict]
    ) -> int:
        """保存生成的脚本
        
        Args:
            topic: 主题
            platform: 平台
            content: 脚本内容
            video_count: 涉及的视频数量
            videos_data: 视频数据列表
            
        Returns:
            int: 生成的脚本ID
        """
        try:
            # 收集相关ID
            video_ids = []
            subtitle_ids = []
            summary_ids = []
            
            for video in videos_data:
                # 确保video不为None
                if not video:
                    continue
                    
                # 获取视频ID
                video_id = video.get('id')
                if video_id is not None:
                    video_ids.append(video_id)
                
                # 获取字幕ID
                subtitle = video.get('subtitle')
                if subtitle and isinstance(subtitle, dict):
                    subtitle_id = subtitle.get('id')
                    if subtitle_id is not None:
                        subtitle_ids.append(subtitle_id)
                
                # 获取总结ID 
                point_summary = video.get('point_summary')
                if point_summary and isinstance(point_summary, dict):
                    summary_id = point_summary.get('id')
                    if summary_id is not None:
                        summary_ids.append(summary_id)
            
            with self._db_transaction() as db:
                script = GeneratedScript(
                    topic=topic,
                    platform=platform,
                    content=content,
                    video_count=video_count,
                    video_ids=video_ids,
                    subtitle_ids=subtitle_ids,
                    summary_ids=summary_ids
                )
                db.add(script)
                db.flush()
                
                print(f"脚本保存成功: id={script.id}, 主题={topic}, 平台={platform.value}")
                return script.id
                
        except Exception as e:
            print(f"保存生成的脚本失败: {str(e)}")
            raise
            
    def get_generated_script(self, script_id: int) -> Optional[Dict]:
        """获取生成的脚本及相关信息
        
        Args:
            script_id: 脚本ID
            
        Returns:
            Optional[Dict]: 脚本信息及相关数据
        """
        try:
            with get_db() as db:
                script = db.query(GeneratedScript).filter(
                    GeneratedScript.id == script_id
                ).first()
                
                if not script:
                    return None
                    
                # 获取相关视频信息
                videos = db.query(Video).filter(
                    Video.id.in_(script.video_ids)
                ).all()
                
                # 获取相关字幕信息
                subtitles = db.query(Subtitle).filter(
                    Subtitle.id.in_(script.subtitle_ids)
                ).all()
                
                # 获取相关总结信息
                summaries = db.query(SubtitleSummary).filter(
                    SubtitleSummary.id.in_(script.summary_ids)
                ).all()
                
                return {
                    'id': script.id,
                    'topic': script.topic,
                    'platform': script.platform.value,
                    'content': script.content,
                    'video_count': script.video_count,
                    'create_time': script.create_time.isoformat(),
                    'update_time': script.update_time.isoformat(),
                    'videos': [
                        {
                            'id': v.id,
                            'title': v.title,
                            'author': v.author,
                            'platform_vid': v.platform_vid
                        }
                        for v in videos
                    ],
                    'subtitles': [
                        {
                            'id': s.id,
                            'content': s.content,
                            'language': s.language,
                            'source': s.source.value
                        }
                        for s in subtitles
                    ],
                    'summaries': [
                        {
                            'id': s.id,
                            'content': s.content,
                            'create_time': s.create_time.isoformat()
                        }
                        for s in summaries
                    ]
                }
                
        except Exception as e:
            print(f"获取脚本信息失败: {str(e)}")
            raise
            
    def get_scripts_by_topic(self, topic: str, platform: Optional[Platform] = None) -> List[Dict]:
        """根据主题获取脚本列表
        
        Args:
            topic: 主题
            platform: 平台（可选）
            
        Returns:
            List[Dict]: 脚本列表
        """
        try:
            with get_db() as db:
                query = db.query(GeneratedScript).filter(
                    GeneratedScript.topic == topic
                )
                
                if platform:
                    query = query.filter(GeneratedScript.platform == platform)
                    
                scripts = query.order_by(GeneratedScript.create_time.desc()).all()
                
                return [
                    {
                        'id': s.id,
                        'topic': s.topic,
                        'platform': s.platform.value,
                        'content': s.content,
                        'video_count': s.video_count,
                        'create_time': s.create_time.isoformat(),
                        'update_time': s.update_time.isoformat()
                    }
                    for s in scripts
                ]
                
        except Exception as e:
            print(f"获取脚本列表失败: {str(e)}")
            raise 

    async def process_subtitle_summary(self, topic: str, subtitle_id: int, content: str) -> None:
        """异步处理字幕总结（新流程）"""
        try:
            # 在同一个数据库会话中获取所有需要的信息
            with self._db_transaction() as db:
                # 检查是否已存在总结
                existing_summary = db.query(SubtitleSummary).filter(
                    SubtitleSummary.subtitle_id == subtitle_id
                ).first()
                
                if existing_summary and existing_summary.content:
                    return

                # 获取字幕信息
                subtitle = db.query(Subtitle).filter(
                    Subtitle.id == subtitle_id
                ).first()
                
                if not subtitle:
                    print(f"未找到字幕记录: {subtitle_id}")
                    return
                
                # 获取关联视频信息
                video = db.query(Video).filter(
                    Video.id == subtitle.video_id
                ).first()
                
                if not video:
                    print(f"未找到关联视频: {subtitle.video_id}")
                    return

                # 保存需要的信息，避免在会话外使用
                subtitle_language = subtitle.language
                video_title = video.title
                video_source_type = video.source_type
                platform_vid = video.platform_vid

            # 在数据库会话外调用外部API
            keypoints_result = await self.coze_client.run_keypoints_workflow(
                topic=topic,
                subtitle=content,
                language=subtitle_language,
                title=video_title,
                source=video_source_type
            )
            
            if not keypoints_result:
                print("关键点提取失败")
                return

            # 检查视频是否与主题相关
            if not keypoints_result.get('association'):
                print(f"视频 {platform_vid} 与主题 '{topic}' 无关联")
                return

            # 检查是否有关键点
            if not keypoints_result.get('key_points'):
                print(f"视频 {platform_vid} 未提取到关键点")
                return

            # 直接拼接关键点内容
            full_summary = "\n\n".join([
                f"【{kp['point']}】\n{kp['content']}"
                for kp in keypoints_result['key_points']
                if kp.get('point') and kp.get('content')
            ])

            # 在新的数据库会话中保存结果
            with self._db_transaction() as db:
                summary = db.query(SubtitleSummary).filter(
                    SubtitleSummary.subtitle_id == subtitle_id
                ).first()
                
                if not summary:
                    summary = SubtitleSummary(
                        subtitle_id=subtitle_id,
                        content=full_summary,
                        key_points=keypoints_result['key_points'],
                        association=keypoints_result['association'],
                        score=keypoints_result['score'],
                        status=TaskStatus.COMPLETED
                    )
                    db.add(summary)
                else:
                    summary.content = full_summary
                    summary.key_points = keypoints_result['key_points']
                    summary.association = keypoints_result['association']
                    summary.score = keypoints_result['score']
                    summary.status = TaskStatus.COMPLETED

        except Exception as e:
            print(f"处理字幕总结失败: {str(e)}")

    async def generate_topic_script(self, topic: str, keyword: str, platform: Platform) -> Optional[str]:
        """为指定主题生成脚本
        
        Args:
            topic: 主题
            keyword
            platform: 平台
            
        Returns:
            Optional[str]: 生成的脚本内容
        """
        try:
            # 获取相关视频的字幕和总结
            videos_data = self.get_videos_with_subtitles_and_summaries(
                platform=platform,
                search_keyword=keyword
            )
            
            if not videos_data:
                print(f"未找到相关视频数据: topic={topic}")
                return None
                
            # 构建工作流输入
            subtitles = []
            for video in videos_data:
                if video.get('subtitle') and video.get('point_summary'):
                    # 检查point_summary的content是否为空
                    point_summary_content = video['point_summary'].get('content', '')
                    if not point_summary_content:
                        continue
                        
                    subtitle_item = {
                        "subtitle": point_summary_content,
                        "title": video.get('title', ''),
                        "video_url": get_video_url(video.get('platform_vid'), platform),
                        "language": video['subtitle'].get('language', 'zh')
                    }
                    subtitles.append(subtitle_item)
            if not subtitles:
                print("没有找到可用的字幕总结")
                return None
                
            # 调用脚本生成工作流
            script = self.coze_client.run_script_workflow(
                topic=topic,
                subtitles=subtitles
            )
            
            if script:
                # 保存生成的脚本
                self.save_generated_script(
                    topic=topic,
                    platform=platform,
                    content=script,
                    video_count=len(videos_data),
                    videos_data=videos_data
                )
                
            return script
            
        except Exception as e:
            print(f"生成主题脚本失败: {str(e)}")
            return None 
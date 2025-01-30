from typing import Optional, Dict, List, Union
from datetime import datetime, timedelta
from db.init.base import get_db
from db.models.subtitle import Video, Subtitle, SubtitleSource, Platform
from pathlib import Path
import uuid
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
import sys

class SubtitleManager:
    def __init__(self):
        pass
        
    def get_video_info(self, platform: str, platform_vid: str) -> Optional[Dict]:
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

    @contextmanager
    def transaction(self) -> GeneratorExit:
        """事务管理器"""
        with get_db() as db:
            try:
                yield db
                db.commit()
            except Exception as e:
                db.rollback()
                raise

    def save_video_info(
        self, 
        video_info: Dict, 
        platform: Platform,
        audio_path: Optional[str] = None
    ) -> str:
        """保存视频信息，返回内部video_id"""
        try:
            print(f"开始保存视频信息: {video_info.get('id')}")
            with self.transaction() as db:
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

    def save_subtitle(
        self,
        video_id: str,
        content: Union[str, Dict],  # 可以接收字符串或字典格式的内容
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
            with self.transaction() as db:
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
                timed_content = None
                detected_language = language  # 默认使用传入的语言
                
                if isinstance(content, str):
                    # 检查是否为WebVTT格式
                    if "WEBVTT" in content or "-->" in content:
                        segments = []
                        lines = content.split('\n')
                        current_text = []
                        current_time = None
                        metadata = {}
                        
                        # 解析WebVTT头部信息
                        for line in lines:
                            line = line.strip()
                            if line.startswith('Kind:'):
                                metadata['kind'] = line.split(':', 1)[1].strip()
                            elif line.startswith('Language:'):
                                lang = line.split(':', 1)[1].strip()
                                # 标准化语言代码 (例如 'en-US' -> 'en')
                                detected_language = lang.split('-')[0].lower()
                                metadata['language'] = lang
                            elif '-->' in line:
                                break
                        
                        # 解析字幕内容
                        for line in lines:
                            if '-->' in line:
                                time_parts = line.split('-->')
                                start_time = self._parse_timestamp(time_parts[0].strip())
                                end_time = self._parse_timestamp(time_parts[1].strip())
                                current_time = {'start': start_time, 'end': end_time}
                            elif line.strip() and not line.startswith('WEBVTT') and \
                                 not line.startswith('Kind:') and \
                                 not line.startswith('Language:') and \
                                 not line[0].isdigit():
                                current_text.append(line.strip())
                            elif not line.strip() and current_time and current_text:
                                segments.append({
                                    'start': current_time['start'],
                                    'end': current_time['end'],
                                    'text': ' '.join(current_text)
                                })
                                current_text = []
                                current_time = None
                        
                        # 处理最后一段
                        if current_time and current_text:
                            segments.append({
                                'start': current_time['start'],
                                'end': current_time['end'],
                                'text': ' '.join(current_text)
                            })
                        
                        pure_text = ' '.join(seg['text'] for seg in segments)
                        timed_content = {
                            'type': 'webvtt',
                            'metadata': metadata,
                            'segments': segments
                        }
                    else:
                        # 纯文本
                        pure_text = content
                elif isinstance(content, dict):
                    if 'text' in content:
                        # Whisper格式
                        pure_text = content['text']
                        if 'segments' in content:
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
                        # yt-dlp格式
                        segments = []
                        texts = []
                        
                        # 处理不同格式的时间戳
                        for key, value in content.items():
                            if isinstance(key, (int, float)):
                                # 数字时间戳
                                start_time = float(key)
                            else:
                                # 字符串时间戳 (例如 "00:00:00.320")
                                start_time = self._parse_timestamp(key)
                            
                            segments.append({
                                'start': start_time,
                                'text': value
                            })
                            texts.append(value)
                        
                        pure_text = ' '.join(texts)
                        timed_content = {
                            'type': 'yt-dlp',
                            'segments': sorted(segments, key=lambda x: x['start'])
                        }
                
                # 创建字幕记录
                subtitle = Subtitle(
                    video_id=video.id,
                    platform_vid=video.platform_vid,
                    platform = platform,
                    source=source,
                    content=pure_text,
                    timed_content=timed_content,
                    language=detected_language,  # 使用检测到的语言
                    model_name=model_name
                )
                db.add(subtitle)
                
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
            with self.transaction() as db:
                subtitle = db.query(Subtitle).filter(
                    Subtitle.platform_vid == video_id
                ).first()
                
                if subtitle:
                    result = {
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
                if video.audio_path and Path(video.audio_path).exists():
                    try:
                        Path(video.audio_path).unlink()
                        video.audio_path = None
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
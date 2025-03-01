import requests
import time
import hashlib
from urllib.parse import urlencode
from typing import List, Dict, Optional
from services.bili2text.core.utils import retry_on_failure
from langchain_community.document_loaders import BiliBiliLoader
import sys
import yt_dlp
import random
import json
import asyncio
from bilibili_api import search
from services.config_service import ConfigurationService


class BilibiliAPI:
    def __init__(self):
        self.search_url = "https://api.bilibili.com/x/web-interface/wbi/search/all/v2"
        self.nav_url = "https://api.bilibili.com/x/web-interface/nav"
        self.view_url = "https://api.bilibili.com/x/web-interface/view"
        self.subtitle_url = "https://api.bilibili.com/x/player/v2"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com'
        }

        config_service = ConfigurationService()
        cookies = {
            'sessdata': config_service.get_config("bilibili_download", "sessdata"),
            'bili_jct': config_service.get_config("bilibili_download", "bili_jct"),
            'buvid3': config_service.get_config("bilibili_download", "buvid3")
        }

        if not all(cookies.values()):
            print("B站Cookies未设置")

        # 设置cookie
        self.sessdata = cookies['sessdata']
        self.bili_jct = cookies['bili_jct']
        self.buvid3 = cookies['buvid3']

        # 初始化会话和WBI密钥
        self.session = requests.Session()
        start_time = time.time()
        self.img_key, self.sub_key = self._get_wbi_keys()
        print(f"获取WBI keys耗时: {time.time() - start_time:.2f}秒")

    def _get_wbi_keys(self) -> tuple:
        """获取WBI签名所需的keys"""
        try:
            resp = self.session.get(self.nav_url, headers=self.headers)
            data = resp.json()['data']
            img_url = data['wbi_img']['img_url']
            sub_url = data['wbi_img']['sub_url']

            img_key = img_url.split('/')[-1].split('.')[0]
            sub_key = sub_url.split('/')[-1].split('.')[0]
            return img_key, sub_key
        except Exception as e:
            print(f"获取WBI keys失败: {str(e)}")
            raise

    def _get_mixin_key(self, orig_key: str) -> str:
        """生成混合密钥"""
        MIXIN_KEY_ENC_TAB = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
            27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
            37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
            22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
        ]
        mixed_key = ''.join([orig_key[i] for i in MIXIN_KEY_ENC_TAB])
        return mixed_key[:32]

    def _sign_params(self, params: Dict) -> Dict:
        """对参数进行WBI签名"""
        params['wts'] = int(time.time())
        mixin_key = self._get_mixin_key(self.img_key + self.sub_key)
        sorted_params = dict(sorted(params.items()))
        query = urlencode(sorted_params)
        text = query + mixin_key
        w_rid = hashlib.md5(text.encode()).hexdigest()
        params['w_rid'] = w_rid
        return params

    def search_videos_old(self, keyword: str, max_results: int = 200, batch_size: int = 20) -> List[Dict]:
        """原始的搜索实现方法"""
        try:
            print(f"搜索B站视频: {keyword}, 目标数量: {max_results}")
            videos = []
            remaining = max_results
            page = 1
            retry_count = 0
            max_retries = 3

            while remaining > 0 and retry_count < max_retries:
                current_batch = min(batch_size, remaining)
                
                print(f"获取第{page}页视频，批次大小: {current_batch}")
                
                # 构建搜索参数
                params = {
                    'keyword': keyword,
                    'page': page,
                    'order': 'totalrank',
                    'search_type': 'video',  # 明确指定搜索类型
                    'tids': 0,  # 所有分区
                    'duration': 0  # 所有时长
                }
                
                # 更新请求头，模拟正常浏览器行为
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Referer': 'https://search.bilibili.com',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Cookie': f'SESSDATA={self.sessdata}; bili_jct={self.bili_jct}; buvid3={self.buvid3}'
                }
                
                # 添加WBI签名
                params = self._sign_params(params)
                
                try:
                    # 添加较长的初始延迟
                    initial_delay = random.uniform(10, 15)
                    print(f"初始等待 {initial_delay:.1f} 秒...")
                    time.sleep(initial_delay)
                    
                    response = self.session.get(
                        self.search_url,
                        params=params,
                        headers=headers,
                        timeout=15,
                        proxies=None  # 如果有代理可以在这里配置
                    )
                    
                    if response.status_code == 412:
                        print("触发反爬虫机制，等待更长时间...")
                        retry_count += 1
                        wait_time = random.uniform(30, 60)  # 较长的等待时间
                        print(f"等待 {wait_time:.1f} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if data.get('code') == 0 and 'data' in data and 'result' in data['data']:
                        batch_videos = []
                        for result_group in data['data']['result']:
                            if result_group['result_type'] == 'video':
                                for video in result_group['data']:
                                    if len(batch_videos) < current_batch:
                                        video_info = {
                                            'id': video['bvid'],
                                            'title': video['title'].replace('<em class="keyword">', '').replace('</em>', ''),
                                            'author': video['author'],
                                            'duration': video['duration'],
                                            'view_count': video['play'],
                                            'description': video.get('description', '')
                                        }
                                        batch_videos.append(video_info)
                        
                        if batch_videos:
                            videos.extend(batch_videos)
                            print(f"本批次成功获取 {len(batch_videos)} 个视频")
                            remaining -= len(batch_videos)
                            page += 1
                            retry_count = 0  # 重置重试计数
                            
                            # 批次间的随机延迟
                            if remaining > 0:
                                delay = random.uniform(15, 25)  # 增加延迟时间
                                print(f"等待 {delay:.1f} 秒后继续下一批次")
                                time.sleep(delay)
                        else:
                            print("本页没有找到视频，搜索结束")
                            break
                    else:
                        print(f"接口返回异常: {data}")
                        retry_count += 1
                        time.sleep(random.uniform(20, 30))
                        
                except requests.RequestException as e:
                    print(f"请求失败: {str(e)}")
                    retry_count += 1
                    wait_time = random.uniform(20, 30)
                    print(f"等待 {wait_time:.1f} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                
            if retry_count >= max_retries:
                print("达到最大重试次数，搜索终止")
                
            print(f"搜索完成，共找到 {len(videos)} 个视频")
            return videos

        except Exception as e:
            error_msg = f"B站搜索失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            return []

    async def search_videos(self, keyword: str, max_results: int = 200) -> List[Dict]:
        """使用 bilibili-api 搜索B站视频
        
        Args:
            keyword: 搜索关键词
            max_results: 最大结果数量
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            print(f"搜索B站视频: {keyword}, 目标数量: {max_results}")
            videos = []
            page = 1
            
            while len(videos) < max_results:
                # 使用 bilibili-api 进行搜索
                search_result = await search.search_by_type(
                    keyword,
                    search_type=search.SearchObjectType.VIDEO,
                    page=page
                )
                
                if not search_result['result']:
                    print("没有更多视频结果")
                    break
                
                # 处理搜索结果
                for video in search_result['result']:
                    if len(videos) >= max_results:
                        break
                        
                    # 判断是否为课堂视频
                    is_course = (
                        video.get('type') == 'ketang' or  # 类型为课堂
                        bool(video.get('episode_count_text', '').find('课时') != -1)  # 包含课时信息
                    )
                    if is_course:
                        print(f"跳过课堂视频: {video['title']}")
                        continue
                    
                    # 提取更多必要的视频信息
                    video_info = {
                        'id': video['bvid'],
                        'aid': video['aid'],
                        'title': video['title'].replace('<em class="keyword">', '').replace('</em>', ''),
                        'author': video['author'],
                        'duration': video['duration'],
                        'view_count': video['play'],
                        'description': video.get('description', ''),
                        'pubdate': video.get('pubdate', 0),
                        'cover': video.get('pic', '').lstrip('//'),  # 移除开头的 //
                        'tags': video.get('tag', '').split(','),
                        'danmaku_count': video.get('danmaku', 0),
                        'like_count': video.get('like', 0),
                        'favorite_count': video.get('favorites', 0),
                        'comment_count': video.get('review', 0),
                        'type_name': video.get('typename', '')
                    }
                    videos.append(video_info)
                
                print(f"第{page}页成功获取 {len(search_result['result'])} 个视频")
                page += 1
                
                # 添加随机延迟
                delay = random.uniform(3, 5)
                print(f"等待 {delay:.1f} 秒后继续下一页")
                await asyncio.sleep(delay)
            
            print(f"搜索完成，共找到 {len(videos)} 个视频")
            return videos

        except Exception as e:
            error_msg = f"B站搜索失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            print("出错后切换到备选搜索方法...")
            return self.search_videos_old(keyword, max_results)

            raise

    def get_subtitle(self, bvid: str) -> Optional[str]:
        """获取视频字幕"""
        print(f"尝试获取视频字幕: {bvid}")

        try:
            # 创建BiliBiliLoader实例
            loader = BiliBiliLoader(
                video_urls=[f"https://www.bilibili.com/video/{bvid}"],
                sessdata=self.sessdata,
                bili_jct=self.bili_jct,
                buvid3=self.buvid3
            )

            # 加载视频信息和字幕
            print("正在加载视频信息...")
            docs = loader.load()

            if not docs:
                print("未找到字幕内容")
                return None

            # 获取第一个文档的内容
            content = docs[0].page_content

            # 提取字幕内容
            if content:
                # 检查是否包含标题和描述
                if "Video Title:" in content and "Transcript:" in content:
                    transcript = content.split("Transcript:")[1].strip()
                    print("成功获取字幕内容")
                    return transcript
                # 如果内容不为空但格式不对，可能是错误的字幕
                else:
                    print("获取到的内容格式不正确，可能是错误的字幕")
                    return None

            print("未找到字幕内容")
            return None

        except Exception as e:
            error_msg = f"获取字幕失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            return None

    def get_video_info(self, bvid: str) -> Dict:
        """获取视频详细信息"""
        try:
            print(f"获取视频信息: {bvid}")
            # 构建请求参数
            params = {
                'bvid': bvid
            }

            # 发送请求
            response = self.session.get(
                self.view_url,
                params=params,
                headers=self.headers
            )
            data = response.json()

            if data['code'] != 0:
                error_msg = f"获取视频信息失败: {data['message']}"
                print(error_msg, file=sys.stderr)
                raise Exception(error_msg)

            video_data = data['data']

            # 提取需要的信息
            video_info = {
                'id': bvid,
                'title': video_data.get('title', ''),
                'author': video_data.get('owner', {}).get('name', ''),
                'duration': video_data.get('duration', 0),
                'view_count': video_data.get('stat', {}).get('view', 0),
                'description': video_data.get('desc', ''),
                'tags': video_data.get('tag', []),
                'keywords': [
                    tag.strip()
                    for tag in video_data.get('tag', '').split(',')
                    if tag.strip()
                ],
                'pubdate': video_data.get('pubdate', 0),
                'cid': video_data.get('cid', 0),  # 用于获取字幕
                'aid': video_data.get('aid', 0)
            }

            print(f"成功获取视频信息: {bvid}")
            return video_info

        except Exception as e:
            error_msg = f"获取视频信息失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

    def download_audio(self, url: str, output_path: str) -> str:
        """下载B站音频
        
        Args:
            url: 视频URL
            output_path: 输出文件路径
            
        Returns:
            str: 下载后的文件路径
        """
        try:
            print(f"开始下载B站音频: {url}")
            
            # 从配置服务获取下载选项
            config_service = ConfigurationService()
            base_opts = config_service.get_config("bilibili_download", "base_opts")
            
            # 配置yt-dlp选项
            ydl_opts = base_opts.copy()
            ydl_opts.update({
                'outtmpl': output_path.replace('.mp3', ''),
                # 添加cookies
                'cookies': {
                    'SESSDATA': self.sessdata,
                    'bili_jct': self.bili_jct,
                    'buvid3': self.buvid3
                }
            })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            return output_path
            
        except Exception as e:
            error_msg = f"下载B站音频失败: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise

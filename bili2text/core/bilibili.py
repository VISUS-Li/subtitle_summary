import requests
import time
import hashlib
from urllib.parse import urlencode
from typing import List, Dict, Optional
from ..config import MAX_RETRIES, RETRY_DELAY
from .utils import setup_logger, retry_on_failure
from langchain_community.document_loaders import BiliBiliLoader

logger = setup_logger("bilibili")

class BilibiliAPI:
    def __init__(self, sessdata=None, bili_jct=None, buvid3=None):
        self.search_url = "https://api.bilibili.com/x/web-interface/wbi/search/all/v2"
        self.nav_url = "https://api.bilibili.com/x/web-interface/nav"
        self.view_url = "https://api.bilibili.com/x/web-interface/view"
        self.subtitle_url = "https://api.bilibili.com/x/player/v2"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com'
        }
        
        # 设置cookie
        self.sessdata = sessdata
        self.bili_jct = bili_jct 
        self.buvid3 = buvid3
        
        # 初始化会话和WBI密钥
        self.session = requests.Session()
        self.session.get("https://www.bilibili.com", headers=self.headers)
        self.img_key, self.sub_key = self._get_wbi_keys()

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
            logger.error(f"获取WBI keys失败: {str(e)}")
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

    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)
    def search_videos(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """
        搜索视频并返回结果列表
        
        Args:
            keyword: 搜索关键词
            max_results: 最大返回结果数量
            
        Returns:
            list: 包含视频信息的字典列表
        """
        logger.info(f"搜索关键词: {keyword}, 最大结果数: {max_results}")
        
        params = {
            'keyword': keyword,
            'page': 1,
            'order': 'totalrank'
        }
        
        try:
            params = self._sign_params(params)
            response = self.session.get(
                self.search_url,
                params=params,
                headers=self.headers
            ).json()
            
            videos = []
            if 'data' in response and 'result' in response['data']:
                for result_group in response['data']['result']:
                    if result_group['result_type'] == 'video':
                        for video in result_group['data']:
                            video_info = {
                                'bvid': video['bvid'],
                                'title': video['title'].replace('<em class="keyword">', '').replace('</em>', ''),
                                'author': video['author'],
                                'duration': video['duration'],
                                'play_count': video['play']
                            }
                            videos.append(video_info)
                            if len(videos) >= max_results:
                                return videos
            
            logger.info(f"搜索完成，找到 {len(videos)} 个视频")
            return videos
            
        except Exception as e:
            logger.error(f"搜索视频失败: {str(e)}")
            raise

    @retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY)
    def get_subtitle(self, bvid: str) -> Optional[str]:
        """获取视频字幕"""
        logger.info(f"尝试获取视频字幕: {bvid}")
        
        try:
            # 创建BiliBiliLoader实例
            loader = BiliBiliLoader(
                video_urls=[f"https://www.bilibili.com/video/{bvid}"],
                sessdata=self.sessdata,
                bili_jct=self.bili_jct,
                buvid3=self.buvid3
            )
            
            # 加载视频信息和字幕
            docs = loader.load()
            
            if not docs:
                logger.info("未找到字幕内容")
                return None
                
            # 获取第一个文档的内容
            content = docs[0].page_content
            
            # 提取字幕内容
            if content and "Transcript:" in content:
                transcript = content.split("Transcript:")[1].strip()
                return transcript
                
            logger.info("未找到字幕内容")
            return None
            
        except Exception as e:
            logger.error(f"获取字幕失败: {str(e)}")
            return None
        
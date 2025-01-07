import requests
import time
import hashlib
from urllib.parse import urlencode
import re
from typing import TypedDict, List

# 条件导入 runtime 相关的包
try:
    from runtime import Args
    from typings.ces.ces import Input, Output
    IN_HANDLER_MODE = True
except ImportError:
    IN_HANDLER_MODE = False


class VideoInfo(TypedDict):
    title: str
    author: str
    mid: int
    bvid: str
    aid: int
    play: int
    like: int
    favorites: int
    danmaku: int
    duration: str
    pubdate: int
    description: str
    pic: str
    typename: str
    tag: str
    arcurl: str

class PageInfo(TypedDict):
    page: int
    pagesize: int
    numResults: int
    numPages: int
        # 当作为普通脚本运行时的类型定义
class Input(TypedDict):
    keyword: str
    page: int
    page_size: int  # 新增：每页数量
    order: str      # 新增：排序方式
    duration: int   # 新增：视频时长筛选

class Output(TypedDict):
    page_info: PageInfo
    videos: List[VideoInfo]

class BilibiliSearch:
    def __init__(self):
        self.search_url = "https://api.bilibili.com/x/web-interface/wbi/search/all/v2"
        self.nav_url = "https://api.bilibili.com/x/web-interface/nav"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com'
        }
        # 先访问主站获取cookies
        self.session = requests.Session()
        self.session.get("https://www.bilibili.com", headers=self.headers)
        
        # 获取WBI签名所需的keys
        self.img_key, self.sub_key = self._get_wbi_keys()

        self.valid_orders = {
            "totalrank": "综合排序",
            "pubdate": "最新发布",
            "click": "最多点击",
            "dm": "最多弹幕",
            "stow": "最多收藏",
        }
        self.valid_durations = {
            0: "全部时长",
            1: "0-10分钟",
            2: "10-30分钟",
            3: "30-60分钟",
            4: "60分钟以上",
        }

    def _get_wbi_keys(self):
        """获取WBI签名所需的img_key和sub_key"""
        resp = self.session.get(self.nav_url, headers=self.headers)
        data = resp.json()['data']
        img_url = data['wbi_img']['img_url']
        sub_url = data['wbi_img']['sub_url']
        
        img_key = img_url.split('/')[-1].split('.')[0]
        sub_key = sub_url.split('/')[-1].split('.')[0]
        return img_key, sub_key

    def _get_mixin_key(self, orig_key):
        """生成混合密钥"""
        MIXIN_KEY_ENC_TAB = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
            27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
            37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
            22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
        ]
        mixed_key = ''.join([orig_key[i] for i in MIXIN_KEY_ENC_TAB])
        return mixed_key[:32]

    def _sign_params(self, params):
        """对参数进行WBI签名"""
        # 添加时间戳
        params['wts'] = int(time.time())
        
        # 合并key
        mixin_key = self._get_mixin_key(self.img_key + self.sub_key)
        
        # 按照字母顺序排序参数
        sorted_params = dict(sorted(params.items()))
        
        # 将参数转换为url编码格式并拼接密钥
        query = urlencode(sorted_params)
        text = query + mixin_key
        
        # 计算MD5作为签名
        w_rid = hashlib.md5(text.encode()).hexdigest()
        
        params['w_rid'] = w_rid
        return params

    def search(self, keyword: str, page: int = 1, page_size: int = 20, order: str = "totalrank", duration: int = 0):
        """执行搜索
        Args:
            keyword: 搜索关键词
            page: 页码，从1开始
            page_size: 每页数量，默认20
            order: 排序方式，可选值：totalrank(综合), pubdate(最新), click(最多点击), dm(最多弹幕), stow(最多收藏)
            duration: 时长筛选，可选值：0(全部), 1(0-10分钟), 2(10-30分钟), 3(30-60分钟), 4(60分钟以上)
        """
        if order not in self.valid_orders:
            raise ValueError(f"无效的排序方式，可选值：{list(self.valid_orders.keys())}")
        if duration not in self.valid_durations:
            raise ValueError(f"无效的时长筛选，可选值：{list(self.valid_durations.keys())}")
            
        params = {
            'keyword': keyword,
            'page': page,
            'page_size': page_size,
            'order': order,
            'duration': duration,
            'search_type': 'video'  # 限定只搜索视频
        }
        
        # 添加WBI签名
        params = self._sign_params(params)
        
        response = self.session.get(
            self.search_url,
            params=params,
            headers=self.headers
        )
        
        return response.json()

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def search_bilibili(keyword: str, page: int = 1, page_size: int = 2,
                   order: str = "totalrank", duration: int = 0) -> Output:
    """普通函数方式调用"""
    # 验证必要参数
    if not keyword or not isinstance(keyword, str):
        raise ValueError("搜索关键词不能为空且必须是字符串类型")
    if not isinstance(page, int) or page < 1:
        raise ValueError("页码必须是大于0的整数")
    
    bilibili = BilibiliSearch()
    results = bilibili.search(keyword, page, page_size, order, duration)
    
    # 检查返回状态码
    if results.get('code') != 0:  # bilibili API 成功时 code 为 0
        error_msg = results.get('message', '未知错误')
        raise Exception(f"搜索失败: {error_msg}")
    
    # 确保data字段存在
    if 'data' not in results:
        raise Exception("返回数据格式错误: 缺少 data 字段")
    
    # 构建页面信息
    page_info: PageInfo = {
        "page": results['data']['page'],
        "pagesize": results['data']['pagesize'],
        "numResults": results['data']['numResults'],
        "numPages": results['data']['numPages']
    }
    
    videos: List[VideoInfo] = []
    
    # 处理视频信息
    for item in results['data']['result']:
        if item['result_type'] == 'video':
            for video in item['data']:
                video_info: VideoInfo = {
                    "title": remove_html_tags(video['title']),
                    "author": video['author'],
                    "mid": video['mid'],
                    "bvid": video['bvid'],
                    "aid": video['aid'],
                    "play": video['play'],
                    "like": video['like'],
                    "favorites": video['favorites'],
                    "danmaku": video['danmaku'],
                    "duration": video['duration'],
                    "pubdate": video['pubdate'],
                    "description": video['description'],
                    "pic": video['pic'],
                    "typename": video.get('typename', ''),
                    "tag": video.get('tag', ''),
                    "arcurl": video['arcurl']
                }
                videos.append(video_info)
    
    return {
        "page_info": page_info,
        "videos": videos
    }

def handler(args: 'Args[Input]') -> Output:
    """Handler 方式调用"""
    try:
        # 验证输入参数
        if not hasattr(args, 'input'):
            raise ValueError("缺少输入参数")
            
        input_data = args.input
        keyword = getattr(input_data, 'keyword', None)
        page = getattr(input_data, 'page', 1)
        page_size = getattr(input_data, 'page_size', 20)
        order = getattr(input_data, 'order', 'totalrank')
        duration = getattr(input_data, 'duration', 0)
        if page == None or page <= 0:
            page = 1
        if page_size == None or page_size <= 0:
            page_size = 20
        if order == None or order not in ['totalrank', 'pubdate', 'click', 'dm', 'stow']:
            order = 'totalrank'
        if duration == None or duration not in [0, 1, 2, 3, 4]:
            duration = 0

        
        if not keyword:
            raise ValueError("缺少必要参数: keyword")
            
        return search_bilibili(
            keyword=keyword,
            page=page,
            page_size=page_size,
            order=order,
            duration=duration
        )
    except Exception as e:
        if IN_HANDLER_MODE and hasattr(args, 'logger'):
            args.logger.error(f"搜索出错: {str(e)}")
        raise

if __name__ == '__main__':
    # 普通方式运行的示例
    import json
    
    # 测试搜索
    keyword = input("请输入搜索关键词: ").strip()
    if not keyword:
        print("错误: 搜索关键词不能为空")
        exit(1)
        
    try:
        page_input = input("请输入页码(默认1): ").strip()
        page = int(page_input) if page_input else 1
        if page < 1:
            raise ValueError("页码必须大于0")
    except ValueError as e:
        if str(e) == "页码必须大于0":
            print("错误: " + str(e))
        else:
            print("错误: 页码必须是整数")
        exit(1)
    
    try:
        results = search_bilibili(keyword, page)
        
        # 打印搜索结果
        print("\n搜索结果:")
        print(f"页面信息: {json.dumps(results['page_info'], ensure_ascii=False, indent=2)}")
        print(f"\n找到 {len(results['videos'])} 个视频:")
        
        for i, video in enumerate(results['videos'], 1):
            print(f"\n{i}. {video['title']}")
            print(f"   作者: {video['author']}")
            print(f"   播放: {video['play']} | 点赞: {video['like']} | 收藏: {video['favorites']}")
            print(f"   链接: {video['arcurl']}")
    except Exception as e:
        print(f"错误: {str(e)}")
import requests
import time
import hashlib
from urllib.parse import urlencode

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

    def search(self, keyword):
        """执行搜索"""
        params = {
            'keyword': keyword,
            'page': 1,
            'order': 'totalrank'  # 默认综合排序
        }
        
        # 添加WBI签名
        params = self._sign_params(params)
        
        response = self.session.get(
            self.search_url,
            params=params,
            headers=self.headers
        )
        
        return response.json()

# 使用示例
if __name__ == "__main__":
    bilibili = BilibiliSearch()
    results = bilibili.search("AI")
    print(results) 
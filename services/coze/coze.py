from typing import Dict, Optional, Any, List
import json
import time
import jwt
import requests
from pathlib import Path
from .config import CozeConfig

class CozeClient:
    def __init__(self, config: CozeConfig):
        self.config = config
        self.base_url = config.base_url
        self.app_id = config.app_id
        self.public_key = config.public_key
        self.private_key_path = config.private_key_path
        self.http_timeout = config.http_timeout
        
        self.access_token = None
        self.expiry = 0
        self._load_private_key()
        
    def _load_private_key(self):
        """加载RSA私钥"""
        try:
            with open(self.private_key_path, 'r') as f:
                self.private_key = f.read()
        except Exception as e:
            raise Exception(f"读取私钥文件失败: {str(e)}")
            
    def _authenticate(self):
        """获取访问令牌"""
        if self.access_token and time.time() < self.expiry - 60:
            return
            
        # 生成JWT
        now = int(time.time())
        claims = {
            'iss': self.app_id,
            'aud': 'api.coze.cn',
            'exp': now + 3600,
            'iat': now,
            'jti': str(int(time.time() * 1000))
        }
        
        headers = {
            'kid': self.public_key,
            'typ': 'JWT'
        }
        
        try:
            token = jwt.encode(
                claims,
                self.private_key,
                algorithm='RS256',
                headers=headers
            )
        except Exception as e:
            raise Exception(f"生成JWT失败: {str(e)}")
            
        # 请求访问令牌
        url = f"{self.base_url}/api/permission/oauth2/token"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'duration_seconds': 86399,
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.http_timeout)
            response.raise_for_status()
            result = response.json()
            
            self.access_token = result['access_token']
            self.expiry = time.time() + result['expires_in']
        except Exception as e:
            raise Exception(f"获取访问令牌失败: {str(e)}")
            
    def workflow_run(self, workflow_id: str, parameters: Dict = None, bot_id: str = None, ext: Dict = None) -> Dict:
        """
        执行工作流(非流式)
        """
        self._authenticate()
        
        url = f"{self.base_url}/v1/workflow/run"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'workflow_id': workflow_id
        }
        
        if parameters:
            payload['parameters'] = parameters
        if bot_id:
            payload['bot_id'] = bot_id
        if ext:
            payload['ext'] = ext
            
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.http_timeout)
            response.raise_for_status()
            result = response.json()
            
            if result['code'] != 0:
                raise Exception(f"工作流运行失败: {result['msg']}")
                
            # 构造返回事件
            return {
                'id': 1,  # 非流式只有一个消息
                'event': 'message',
                'data': {
                    'content': result['data'],
                    'content_type': 'text',
                    'node_title': '完成',
                    'node_is_finish': True,
                    'cost': float(result['cost'])
                }
            }
        except Exception as e:
            raise Exception(f"执行工作流失败: {str(e)}")
    
    def run_summary_workflow(
        self, 
        topic: str,
        subtitle: str,
        language: str = 'zh',
        title: str = '',
        source: str = ''
    ) -> Dict:
        """
        执行字幕总结工作流
        
        Args:
            topic: 主题
            subtitle: 需要总结的字幕内容
            language: 语言，默认中文
            title: 标题
            source: 来源
            
        Returns:
            Dict: {
                "association": bool,  # 是否相关
                "summarized_subtitle": str,  # 总结的字幕内容
                "score": int  # 相关性得分
            }
        """
        workflow_id = self.config.workflow_ids.get('WORKFLOW_SUMMARY')
        if not workflow_id:
            raise ValueError("未配置WORKFLOW_SUMMARY工作流ID")
            
        parameters = {
            "topic": topic,
            "subtitle": subtitle,
            "language": language,
            "title": title,
            "source": source
        }
        
        result = self.workflow_run(workflow_id, parameters=parameters)
        
        try:
            content = result['data']['content']
            if isinstance(content, str):
                content = json.loads(content)
            return content
        except Exception as e:
            raise Exception(f"解析总结工作流返回数据失败: {str(e)}")
    
    def run_script_workflow(
        self, 
        topic: str,
        subtitles: List[Dict[str, str]]
    ) -> str:
        """
        执行脚本生成工作流
        
        Args:
            topic: 主题
            subtitles: 字幕列表，每个字幕包含：
                - subtitle: 字幕内容
                - title: 标题
                - language: 语言
            
        Returns:
            str: 生成的脚本内容
        """
        workflow_id = self.config.workflow_ids.get('WORKFLOW_SCRIPT')
        if not workflow_id:
            raise ValueError("未配置WORKFLOW_SCRIPT工作流ID")
        
        # 验证字幕列表的格式
        for item in subtitles:
            if not all(key in item for key in ['subtitle', 'title', 'language']):
                raise ValueError("字幕列表格式错误，每个字幕必须包含 subtitle、title 和 language 字段")
            
        parameters = {
            "topic": topic,
            "subtitles": subtitles
        }
        
        result = self.workflow_run(workflow_id, parameters=parameters)
        return result['data']['content']
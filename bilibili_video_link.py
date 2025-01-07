from typing import TypedDict
import requests

# 条件导入 runtime 相关的包
try:
    from runtime import Args
    from typings.ces.ces import Input, Output
    IN_HANDLER_MODE = True
except ImportError:
    IN_HANDLER_MODE = False

class Input(TypedDict):
    bv_id: str

class Output(TypedDict):
    title: str
    video_url: str

def extract_bv_id(input_str: str) -> str:
    """从输入中提取BV号
    支持完整B站视频链接或直接的BV号
    Args:
        input_str: 视频链接或BV号
    Returns:
        提取的BV号
    """
    # 移除首尾空白
    input_str = input_str.strip()
    
    # 尝试从URL中提取BV号
    if 'bilibili.com' in input_str:
        import re
        bv_pattern = r'BV[a-zA-Z0-9]{10}'
        match = re.search(bv_pattern, input_str)
        if match:
            return match.group(0)
    
    # 如果输入本身就是BV号（可能带有'BV'前缀）
    if input_str.upper().startswith('BV'):
        return input_str
    
    raise ValueError("无法识别的视频链接或BV号格式")

def get_bilibili_video_url(bv_id: str) -> Output:
    """获取B站视频直链
    Args:
        bv_id: 视频链接或BV号
    Returns:
        包含视频标题和直链的字典
    """
    # 首先提取BV号
    bv_id = extract_bv_id(bv_id)
    # 移除可能包含的'BV'前缀
    bv_id = bv_id.strip('BV')
    
    try:
        # 构建第一个API URL获取视频信息
        meta_url = f'https://bili.zhouql.vip/meta/BV{bv_id}'
        
        # 发送第一个GET请求获取视频信息
        response = requests.get(meta_url)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['code'] == 0:
                # 获取aid和cid
                video_info = data['data']
                aid = video_info['aid']
                cid = video_info['cid']
                title = video_info['title']
                
                # 构建第二个API URL获取视频直链
                download_url = f'https://bili.zhouql.vip/download/{aid}/{cid}'
                
                # 发送第二个GET请求获取视频直链
                download_response = requests.get(download_url)
                
                if download_response.status_code == 200:
                    download_data = download_response.json()
                    
                    if download_data['code'] == 0:
                        return {
                            "title": title,
                            "video_url": download_data['data']['durl'][0]['url']
                        }
                    else:
                        print(f'获取视频直链失败: {download_data["message"]}')
                        return None
                        
            else:
                print(f'获取视频信息失败: {data["message"]}')
                return None
                
    except Exception as e:
        print(f'发生错误: {str(e)}')
        return None

def handler(args: 'Args[Input]') -> Output:
    """Handler 方式调用"""
    try:
        if not hasattr(args, 'input'):
            raise ValueError("缺少输入参数")
            
        input_data = args.input
        bv_id = getattr(input_data, 'bv_id', None)
        
        if not bv_id:
            raise ValueError("缺少必要参数: bv_id")
            
        return get_bilibili_video_url(bv_id)
    except Exception as e:
        if IN_HANDLER_MODE and hasattr(args, 'logger'):
            args.logger.error(f"获取视频直链出错: {str(e)}")
        raise

if __name__ == '__main__':
    # 普通方式运行的示例
    bv_id = input("请输入视频链接或BV号: ").strip()
    if not bv_id:
        print("错误: 输入不能为空")
        exit(1)
        
    try:
        result = get_bilibili_video_url(bv_id)
        print(f"\n获取成功:")
        print(f"视频标题: {result['title']}")
        print(f"视频直链: {result['video_url']}")
    except Exception as e:
        print(f"错误: {str(e)}")

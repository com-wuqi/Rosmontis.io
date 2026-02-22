import hashlib
import hmac
import time

from . import config


# Powered by AI, rewrite by com-wuqi

def generate_signature(timestamp: int) -> str:
    """
    生成 HMAC-SHA256 签名
    :param timestamp: UNIX 时间戳（秒）
    :return: 签名字符串（64字符十六进制小写）
    """

    api_key: str = config.api_key
    secret_key: str = config.api_secret

    # 构造签名字符串
    sign_string = f"key={api_key}&timestamp={timestamp}"

    # 使用 Secret Key 计算 HMAC-SHA256
    signature = hmac.new(
        key=secret_key.encode('utf-8'),
        msg=sign_string.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    return signature


def build_headers(timestamp: int = None) -> dict:
    """
    构造包含认证信息的请求头
    :param timestamp: UNIX 时间戳（秒），若为 None 则自动获取当前时间
    :return: 请求头字典
    """
    api_key: str = config.api_key
    if timestamp is None:
        timestamp = int(time.time())

    signature = generate_signature(timestamp)

    headers = {
        "X-Api-Key": api_key,
        "X-Api-Timestamp": str(timestamp),
        "X-Api-Sign": signature,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    return headers

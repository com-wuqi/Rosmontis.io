import json
import uuid
from typing import Optional

import websockets
from nonebot.log import logger

from . import configs


def parse_cookie_string(cookie_str: str) -> dict:
    """
    解析 Cookie 字符串为字典
    示例输入："uin=o3226526374; skey=@xxx; p_skey=@yyy"
    示例输出：{"uin": "o3226526374", "skey": "@xxx", "p_skey": "@yyy"}
    """
    cookies = {}
    if not cookie_str:
        return cookies

    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()

    return cookies


class OneBotUploadTester:
    def __init__(self, ws_url: str = configs.ws_url, access_token: Optional[str] = configs.ws_token):
        self.ws_url = ws_url
        self.access_token = access_token
        self.websocket = None

    async def connect(self):
        """连接到 OneBot WebSocket"""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        # print(f"连接到 {self.ws_url}")
        self.websocket = await websockets.connect(self.ws_url, additional_headers=headers)
        # print("WebSocket 连接成功")

    async def disconnect(self):
        """断开 WebSocket 连接"""
        if self.websocket:
            await self.websocket.close()
            # print("WebSocket 连接已断开")

    async def get_cookies(self, echo: str = str(uuid.uuid4())) -> dict:
        message = {
            "action": "get_cookies",
            "params": {"domain": "user.qzone.qq.com"},
            "echo": echo
        }
        await self.websocket.send(json.dumps(message))
        while True:
            response = await self.websocket.recv()
            data = json.loads(response)

            # 检查是否是我们的响应
            if data.get("echo") == echo:
                return data
            else:
                continue

    async def get_client_key(self, echo: str = str(uuid.uuid4())) -> dict:
        message = {
            "action": "get_clientkey",
            "params": {},
            "echo": echo
        }
        await self.websocket.send(json.dumps(message))
        while True:
            response = await self.websocket.recv()
            data = json.loads(response)

            # 检查是否是我们的响应
            if data.get("echo") == echo:
                return data
            else:
                continue


async def get_key_dict_by_napcat():
    is_uploader = False
    is_connect = False
    try:
        uploader = OneBotUploadTester()
        is_uploader = True
        await uploader.connect()
        is_connect = True
        data_res2 = await uploader.get_cookies()
        await uploader.disconnect()
        return parse_cookie_string(data_res2["data"]["cookies"])
    except Exception as e:
        logger.warning("get_key_dict_by_napcat: {}".format(e))
        if is_connect and is_uploader:
            await uploader.disconnect()
    finally:
        pass


async def get_client_key_by_napcat():
    is_uploader = False
    is_connect = False
    try:
        uploader = OneBotUploadTester()
        is_uploader = True
        await uploader.connect()
        is_connect = True
        data_res2 = await uploader.get_client_key()
        await uploader.disconnect()
        return data_res2["data"]["clientkey"]
    except Exception as e:
        logger.warning("get_client_key_by_napcat: {}".format(e))
        if is_connect and is_uploader:
            await uploader.disconnect()
    finally:
        pass

# if __name__ == '__main__':
#     print(asyncio.run(get_key_dict_by_napcat()))
#     print(asyncio.run(get_client_key_by_napcat()))

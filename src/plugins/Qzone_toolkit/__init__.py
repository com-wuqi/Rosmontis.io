import asyncio
import base64
import json
import os
import re
import traceback
import typing

import httpx
import requests
from nonebot import get_plugin_config, require
from nonebot.log import logger
from nonebot.plugin import PluginMetadata

from .config import Config

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

__plugin_meta__ = PluginMetadata(
    name="Qzone_toolkit",
    description="Qzone-toolkit的nonebot版本QQ空间发送插件",
    usage="提供QQ空间发送服务",
    config=Config,
)

_config = get_plugin_config(Config)
configs = _config.qzone_api
from .napcat_websockets_api import get_key_dict_by_napcat, get_client_key_by_napcat

# 获取插件数据目录
script_dir = store.get_plugin_data_dir()

# ============== 全局常量（无空格）=============
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"

# URL 定义（已清理空格）
qrcode_url = "https://ssl.ptlogin2.qq.com/ptqrshow?appid=549000912&e=2&l=M&s=3&d=72&v=4&t=0.31232733520361844&daid=5&pt_3rd_aid=0"
login_check_url = "https://xui.ptlogin2.qq.com/ssl/ptqrlogin?u1=https://qzs.qq.com/qzone/v5/loginsucc.html?para=izone&ptqrtoken={}&ptredirect=0&h=1&t=1&g=1&from_ui=1&ptlang=2052&action=0-0-1656992258324&js_ver=22070111&js_type=1&login_sig=&pt_uistyle=40&aid=549000912&daid=5&has_onekey=1&&o1vId=1e61428d61cb5015701ad73d5fb59f73"
check_sig_url = "https://ptlogin2.qzone.qq.com/check_sig?pttype=1&uin={}&service=ptqrlogin&nodirect=1&ptsigx={}&s_url=https://qzs.qq.com/qzone/v5/loginsucc.html?para=izone&f_url=&ptlang=2052&ptredirect=100&aid=549000912&daid=5&j_later=0&low_login_hour=0&regmaster=0&pt_login_type=3&pt_aid=0&pt_aaid=16&pt_light=0&pt_3rd_aid=0"

UPLOAD_IMAGE_URL = "https://up.qzone.qq.com/cgi-bin/upload/cgi_upload_image"
EMOTION_PUBLISH_URL = "https://user.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_publish_v6"


# ============== 工具函数 ==============
def generate_gtk(skey: str) -> str:
    """生成 g_tk 值"""
    hash_val = 5381
    for i in range(len(skey)):
        hash_val += (hash_val << 5) + ord(skey[i])
    return str(hash_val & 2147483647)


def get_picbo_and_richval(upload_result: dict):
    """从图片上传结果提取 pic_bo 和 richval"""
    if 'ret' not in upload_result:
        raise Exception("获取图片 picbo 和 richval 失败：缺少 ret 字段")
    if upload_result['ret'] != 0:
        raise Exception(f"上传图片失败：{upload_result.get('msg', '未知错误')}")

    picbo_spt = upload_result['data']['url'].split('&bo=')
    if len(picbo_spt) < 2:
        raise Exception("上传图片失败：无法解析 picbo")

    picbo = picbo_spt[1]
    data = upload_result['data']
    richval = ",{},{},{},{},{},{},,{},{}".format(
        data.get('albumid', ''),
        data.get('lloc', ''),
        data.get('sloc', ''),
        data.get('type', ''),
        data.get('height', ''),
        data.get('width', ''),
        data.get('height', ''),
        data.get('width', '')
    )
    return picbo, richval


# ============== 登录相关 ==============
async def get_clientkey(uin: str) -> str:
    """通过 pt_local_token 获取 clientkey"""
    local_key_url = "https://xui.ptlogin2.qq.com/cgi-bin/xlogin?s_url=https%3A%2F%2Fhuifu.qq.com%2Findex.html&style=20&appid=715021417&proxy_url=https%3A%2F%2Fhuifu.qq.com%2Fproxy.html"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(local_key_url, headers={"User-Agent": UA})
        pt_local_token = resp.cookies.get("pt_local_token")
        if not pt_local_token:
            raise Exception("无法获取 pt_local_token")

        client_key_url = f"https://localhost.ptlogin2.qq.com:4301/pt_get_st?clientuin={uin}&callback=ptui_getst_CB&r=0.7284667321181328&pt_local_tk={pt_local_token}"
        resp = await client.get(
            client_key_url,
            headers={"User-Agent": UA, "Referer": "https://ssl.xui.ptlogin2.qq.com/"},
            cookies=resp.cookies
        )
        if resp.status_code != 200:
            raise Exception(f"获取 clientkey 失败：{resp.status_code}")

        clientKey = resp.cookies.get("clientkey")
        if not clientKey:
            raise Exception("无法获取 clientkey")
        return clientKey


async def get_cookies_via_clientkey(uin: str, clientkey: str) -> dict:
    """通过 clientkey 获取完整 Cookies"""
    login_url = f"https://ssl.ptlogin2.qq.com/jump?ptlang=1033&clientuin={uin}&clientkey={clientkey}&u1=https%3A%2F%2Fuser.qzone.qq.com%2F{uin}%2Finfocenter&keyindex=19"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(login_url, headers={"User-Agent": UA}, follow_redirects=False)
        if "Location" not in resp.headers:
            raise Exception("未获得重定向地址")

        resp = await client.get(
            resp.headers["Location"],
            headers={"User-Agent": UA, "Referer": "https://ssl.xui.ptlogin2.qq.com/"},
            cookies=resp.cookies,
            follow_redirects=False
        )
        cookies = {cookie.name: cookie.value for cookie in resp.cookies.jar}
        return cookies


async def save_cookies_to_file(cookies: dict, file_path: str):
    """保存 Cookies 到文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=4)
    logger.debug(f"Cookies saved to {file_path}")


class QzoneLogin:
    """二维码登录类"""

    def getptqrtoken(self, qrsig: str) -> str:
        e = 0
        for i in range(len(qrsig)):
            e += (e << 5) + ord(qrsig[i])
        return str(2147483647 & e)

    async def login_via_qrcode(self, qrcode_callback: typing.Callable[[bytes], typing.Awaitable[None]],
                               max_timeout_times: int = 3) -> dict:
        for i in range(max_timeout_times):
            req = requests.get(qrcode_url)
            qrsig = ''
            set_cookie = req.headers.get('Set-Cookie', '')
            for part in set_cookie.split(";"):
                if part.strip().startswith("qrsig="):
                    qrsig = part.split("=")[1]
                    break
            if not qrsig:
                raise Exception("qrsig is empty")

            ptqrtoken = self.getptqrtoken(qrsig)
            await qrcode_callback(req.content)

            while True:
                await asyncio.sleep(2)
                check_resp = requests.get(login_check_url.format(ptqrtoken), cookies={"qrsig": qrsig})
                if "二维码已失效" in check_resp.text:
                    break
                if "登录成功" in check_resp.text:
                    response_header_dict = check_resp.headers
                    try:
                        url = eval(check_resp.text.replace("ptuiCB", ""))[2]
                    except Exception as ex:
                        raise Exception("解析登录响应失败") from ex

                    ptsigx_match = re.search(r"ptsigx=([A-Za-z0-9]+)&", url)
                    if not ptsigx_match:
                        raise Exception("无法获取 ptsigx")
                    ptsigx = ptsigx_match.group(1)

                    uin_match = re.search(r"uin=([\d]+)&", url)
                    if not uin_match:
                        raise Exception("无法获取 uin")
                    uin = uin_match.group(1)

                    res = requests.get(
                        check_sig_url.format(uin, ptsigx),
                        cookies={"qrsig": qrsig},
                        headers={'Cookie': response_header_dict.get('Set-Cookie', '')}
                    )
                    final_cookie = res.headers.get('Set-Cookie', '')
                    final_cookie_dict = {}
                    for item in final_cookie.split(";"):
                        parts = item.strip().split("=")
                        if len(parts) == 2 and parts[0] not in final_cookie_dict:
                            final_cookie_dict[parts[0]] = parts[1]
                    return final_cookie_dict
        raise Exception(f"{max_timeout_times}次尝试失败")


# ============== Qzone API 核心类 ==============
class QzoneAPI:
    def __init__(self, cookies_dict: dict):
        self.cookies = cookies_dict
        self.gtk2 = ''
        self.uin = 0
        self.qzonetoken = cookies_dict.get('qzonetoken', '')

        # 计算 g_tk
        if 'p_skey' in self.cookies and self.cookies['p_skey']:
            self.gtk2 = generate_gtk(self.cookies['p_skey'])
        elif 'skey' in self.cookies and self.cookies['skey']:
            self.gtk2 = generate_gtk(self.cookies['skey'])

        # 解析 uin
        if 'uin' in self.cookies:
            try:
                self.uin = int(str(self.cookies['uin']).lstrip('o'))
            except:
                self.uin = 0

        logger.debug(f"QzoneAPI 初始化：uin={self.uin}, g_tk={self.gtk2}, has_qzonetoken={bool(self.qzonetoken)}")

    async def do(self, method: str, url: str, params: dict = None, data: dict = None,
                 headers: dict = None, timeout: int = 10) -> httpx.Response:
        """统一的 HTTP 请求方法"""
        if params is None:
            params = {}
        if data is None:
            data = {}
        if headers is None:
            headers = {}

        # 构建基础请求头（无空格）
        base_headers = {
            'User-Agent': UA,
            'Referer': f'https://user.qzone.qq.com/{self.uin}',
            'Origin': 'https://user.qzone.qq.com',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        base_headers.update(headers)

        # 构建 Cookie 字符串
        cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items() if v])
        base_headers['Cookie'] = cookie_str

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                method=method,
                url=url.strip(),
                params=params,
                data=data,
                headers=base_headers,
                follow_redirects=True
            )
            return resp

    async def upload_image(self, image: bytes) -> dict:
        """上传图片到 QQ 空间"""
        post_data = {
            "filename": "file.jpg",
            "zzpanelkey": "",
            "uploadtype": "1",
            "albumtype": "7",
            "exttype": "0",
            "skey": self.cookies.get("skey", ""),
            "zzpaneluin": self.uin,
            "p_uin": self.uin,
            "uin": self.uin,
            "p_skey": self.cookies.get("p_skey", ""),
            "output_type": "json",
            "qzonetoken": self.qzonetoken,
            "refer": "shuoshuo",
            "charset": "utf-8",
            "output_charset": "utf-8",
            "upload_hd": "1",
            "hd_width": "2048",
            "hd_height": "10000",
            "hd_quality": "96",
            "backUrls": "http://upbak.photo.qzone.qq.com/cgi-bin/upload/cgi_upload_image",
            "base64": "1",
            "picfile": self.image_to_base64(image),
        }

        res = await self.do(
            method="POST",
            url=UPLOAD_IMAGE_URL,
            params={'g_tk': self.gtk2},
            data=post_data,
            timeout=60
        )

        logger.debug(f"上传图片响应：{res.status_code} - {res.text[:100]}")

        if res.status_code == 200:
            try:
                text = res.text.strip()
                # 处理可能的 JSONP 包裹
                if text.startswith('try{') or text.startswith('_Callback('):
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        text = match.group()
                return json.loads(text)
            except Exception as ex:
                logger.error(f"解析上传图片响应失败：{res.text}")
                raise Exception(f"解析上传图片响应失败：{ex}") from ex
        else:
            raise Exception(f"上传图片失败：{res.status_code} - {res.text}")

    def image_to_base64(self, image: bytes) -> str:
        return base64.b64encode(image).decode('utf-8')

    async def publish_emotion(self, content: str, images: list[bytes] = None) -> str:
        """发表说说"""
        if images is None:
            images = []

        post_data = {
            "syn_tweet_verson": "1",
            "paramstr": "1",
            "who": "1",
            "con": content,
            "feedversion": "1",
            "ver": "1",
            "ugc_right": "1",
            "to_sign": "0",
            "hostuin": self.uin,
            "code_version": "1",
            "format": "json",
            "qzreferrer": f"https://user.qzone.qq.com/{self.uin}",
            "qzonetoken": self.qzonetoken,
        }

        if images:
            pic_bos = []
            richvals = []
            for img in images:
                uploadresult = await self.upload_image(img)
                picbo, richval = get_picbo_and_richval(uploadresult)
                pic_bos.append(picbo)
                richvals.append(richval)
            post_data['pic_bo'] = ','.join(pic_bos)
            post_data['richtype'] = '1'
            post_data['richval'] = '\t'.join(richvals)

        logger.debug(f"发表说说：uin={self.uin}, g_tk={self.gtk2}, 内容长度={len(content)}, 图片数={len(images)}")

        res = await self.do(
            method="POST",
            url=EMOTION_PUBLISH_URL,
            params={'g_tk': self.gtk2, 'uin': self.uin, 'qzonetoken': self.qzonetoken},
            data=post_data,
        )

        logger.debug(f"发表说说响应：{res.status_code} - {res.text[:200]}")

        if res.status_code == 200:
            try:
                result = res.json()
                # 检查业务状态码
                if result.get('code') == 0 or result.get('ret') == 0:
                    tid = result.get('tid', result.get('data', {}).get('tid', ''))
                    if tid:
                        return tid
                    else:
                        raise Exception(f"发表成功但未返回 tid: {result}")
                else:
                    raise Exception(f"发表失败：{result}")
            except json.JSONDecodeError:
                raise Exception(f"响应不是 JSON：{res.text}")
            except Exception as ex:
                raise Exception(f"解析发表说说响应失败：{ex}") from ex
        else:
            raise Exception(f"发表说说失败：状态码 {res.status_code}, 响应：{res.text}")


# ============== 自动登录 ==============
async def auto_login(uin: str) -> dict:
    """自动登录：优先 Napcat > clientkey > 二维码"""
    # 尝试 1: Napcat 直接获取 cookie
    try:
        cookies = await get_key_dict_by_napcat()
        if cookies:
            logger.debug("Napcat WebSocket 登录成功")
            return cookies
    except Exception as e:
        logger.debug(f"Napcat WebSocket 登录失败：{e}")

    # 尝试 2: Napcat clientkey
    try:
        clientkey = await get_client_key_by_napcat()
        if clientkey:
            logger.debug(clientkey)
            cookies = await get_cookies_via_clientkey(uin, clientkey)
            logger.debug("Napcat clientkey 登录成功")
            return cookies
    except Exception as e:
        logger.debug(f"Napcat clientkey 登录失败：{e}")

    # 尝试 3: 本地 clientkey
    try:
        clientkey = await get_clientkey(uin)
        cookies = await get_cookies_via_clientkey(uin, clientkey)
        logger.debug("本地 clientkey 登录成功")
        return cookies
    except Exception as e:
        logger.debug(f"本地 clientkey 登录失败：{e}")

    # 尝试 4: 二维码登录
    logger.debug("使用二维码登录")
    login = QzoneLogin()

    async def qrcode_callback(qrcode: bytes):
        qrcode_path = os.path.join(script_dir, "qrcode.png")
        with open(qrcode_path, "wb") as f:
            f.write(qrcode)
        logger.debug(f"二维码已保存：{qrcode_path}")

    cookies = await login.login_via_qrcode(qrcode_callback)
    return cookies


# ============== 发送主函数 ==============
async def send(message: str, image_directory: str = None, qq: str = None) -> None:
    """发送说说主逻辑"""
    if qq is None:
        raise ValueError("必须提供 QQ 号码！")

    cookies_file = os.path.join(script_dir, f"cookies-{qq}.json")
    cookies = None

    # 尝试读取已有 Cookies
    if os.path.exists(cookies_file):
        try:
            with open(cookies_file, 'r', encoding="utf-8") as f:
                cookies = json.load(f)
            logger.debug(f"已读取缓存 Cookies：{list(cookies.keys())}")
        except Exception as e:
            logger.debug(f"读取 cookies 失败：{e}")
            cookies = None

    # 无有效 Cookies 则登录
    if not cookies or not cookies.get('p_skey') and not cookies.get('skey'):
        logger.debug("Cookies 无效，开始登录...")
        attempt = 0
        while attempt < 3:
            try:
                cookies = await auto_login(qq)
                await save_cookies_to_file(cookies, cookies_file)
                qrcode_path = os.path.join(script_dir, "qrcode.png")
                if os.path.exists(qrcode_path):
                    os.remove(qrcode_path)
                logger.debug("登录成功")
                break
            except Exception as e:
                logger.debug(f"登录尝试 {attempt + 1} 失败：{e}")
                traceback.print_exc()
                attempt += 1
                if attempt == 3:
                    raise Exception("连续 3 次登录失败")

    logger.debug(f"最终 Cookies 键：{list(cookies.keys())}")

    qzone = QzoneAPI(cookies)

    # 收集图片
    images = []
    if image_directory and image_directory != "None" and os.path.isdir(image_directory):
        image_files = sorted([
            os.path.join(image_directory, f)
            for f in os.listdir(image_directory)
            if os.path.isfile(os.path.join(image_directory, f))
        ])
        for image_file in image_files:
            with open(image_file, "rb") as img:
                images.append(img.read())
        logger.debug(f"加载图片 {len(images)} 张")

    # 发表说说（失败后重试登录）
    attempt = 0
    while attempt < 3:
        try:
            tid = await qzone.publish_emotion(message, images)
            logger.debug(f"✅ 发表成功，tid: {tid}")
            return
        except Exception as e:
            logger.debug(f"发表尝试 {attempt + 1} 失败：{e}")
            if attempt < 2:
                try:
                    logger.debug("重新登录...")
                    cookies = await auto_login(qq)
                    await save_cookies_to_file(cookies, cookies_file)
                    qzone = QzoneAPI(cookies)
                except Exception as login_err:
                    logger.debug(f"重新登录失败：{login_err}")
            attempt += 1

    raise Exception("连续 3 次发表失败")

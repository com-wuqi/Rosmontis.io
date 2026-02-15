import httpx
from nonebot.log import logger

async def get_a_yiyan() -> str:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("https://v1.hitokoto.cn/")
            if response.status_code == 200:
                data = response.json()
                return data["hitokoto"]
            else:
                logger.warning("yiyan get met error : {}".format(response.status_code))
                return ""
        except Exception as e:
            logger.warning("yiyan get met error : {}".format(e))
            return ""
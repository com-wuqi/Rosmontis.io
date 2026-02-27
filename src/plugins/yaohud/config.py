from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    # 验证方式使用签名校验的方式
    is_enable: bool
    base_url: str
    api_key: str
    api_secret: str
    upload_ws_url: str  # 上传 url
    upload_ws_token: str  # token
    wyvip_cookie: str  # 暂时不使用
    wyvip_level: str  # 音质 , 参考 get_netease_music()
    qqmusic_cookie: str  # 暂时不使用
    qqmusic_level: str  # size 定义歌曲音质，当type=url时有效，留空默认m4a试听音质，可选参数：mp3:普通音质、hq:高品质、sq:无损、hires:HiRes音质

class Config(BaseModel):
    """插件主配置，包含作用域"""
    yaohud: ScopedConfig

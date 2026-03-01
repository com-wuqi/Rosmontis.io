from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    # 验证方式使用签名校验的方式
    is_enable: bool
    base_url: str
    api_key: str
    api_secret: str
    is_enable_upload: bool
    upload_ws_url: str  # 上传 url
    upload_ws_token: str  # token
    wyvip_cookie: str = ""  # 暂时不使用
    wyvip_level: str
    # standard：标准音质 | exhigh：极高音质 |lossless 无损音质 | hires Hi-Res音质 | jyeffect 高清环绕声 | sky：沉浸环绕声 | jymaster：超清母带
    qqmusic_cookie: str = ""  # 暂时不使用
    qqmusic_level: str
    # mp3 : 普通音质、hq : 高品质、flac : 无损
    kuwo_size: str
    # Standard 标准音质, exhigh 极高音质,SQ 超高品质,lossless 无损音质,hires 高解析无损


class Config(BaseModel):
    """插件主配置，包含作用域"""
    yaohud: ScopedConfig

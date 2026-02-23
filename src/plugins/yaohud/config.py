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


class Config(BaseModel):
    """插件主配置，包含作用域"""
    yaohud: ScopedConfig

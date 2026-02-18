from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    websearch_base_url: str
    websearch_api_key: str

class Config(BaseModel):
    """插件主配置，包含作用域"""
    aihelper: ScopedConfig
from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    is_enable_websearch: bool
    websearch_base_url: str
    websearch_api_key: str
    websearch_max_once_calls: int
    websearch_timeout: int

class Config(BaseModel):
    """插件主配置，包含作用域"""
    aihelper: ScopedConfig
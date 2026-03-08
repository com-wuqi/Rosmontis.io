from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    websearch_base_url: str
    websearch_api_key: str
    websearch_timeout: int
    e2b_api_key: str
    e2b_api_url: str



class Config(BaseModel):
    """插件主配置，包含作用域"""
    aiagents: ScopedConfig

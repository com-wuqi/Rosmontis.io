from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    tools_max_once_calls: int
    is_enable_websearch: bool


class Config(BaseModel):
    """插件主配置，包含作用域"""
    aihelper: ScopedConfig
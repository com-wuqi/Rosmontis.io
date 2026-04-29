from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    tools_max_once_calls: int = 20
    is_enable_tool_prompt: bool = True
    api_timeout: int = 300  # api 超时限制


class Config(BaseModel):
    """插件主配置，包含作用域"""
    aihelper: ScopedConfig
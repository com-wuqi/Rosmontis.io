from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    tools_max_once_calls: int = 45
    is_enable_tool_prompt: bool = True
    api_timeout: int = 300  # api 超时限制
    message_queue_timeout: int = 2  # 单个对话超时
    message_queue_max_size: int = 5  # 单个会话最长缓存
    max_workers: int = 10  # 最大worker数，过多会丢弃


class Config(BaseModel):
    """插件主配置，包含作用域"""
    aihelper: ScopedConfig
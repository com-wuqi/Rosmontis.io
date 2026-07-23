from pydantic import BaseModel, Field


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    tools_max_once_calls: int = 45
    is_enable_tool_prompt: bool = True
    api_timeout: int = 300
    message_queue_timeout: int = 2
    message_queue_max_size: int = 5
    max_workers: int = Field(default=10, ge=1)
    redis_url: str = "redis://localhost:6379/0"
    redis_long_expire_time: int = 7 * 24 * 3600  # 7 day
    is_enable_design_prompts: bool = False  # 是否启用含有 design- 标记的提示词


class Config(BaseModel):
    """插件主配置，包含作用域"""
    aihelper: ScopedConfig

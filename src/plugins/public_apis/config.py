from pydantic import BaseModel, Field


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    upload_ws_url: str = ""  # 上传 url
    upload_ws_token: str = ""  # token
    is_enable_upload: bool = False
    global_progress_pool_max_workers: int = Field(default=2, ge=1)
    global_thread_pool_max_workers: int = Field(default=2, ge=1)


class Config(BaseModel):
    """Plugin Config Here"""
    publicapi: ScopedConfig

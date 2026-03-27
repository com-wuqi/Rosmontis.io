from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool = False


class Config(BaseModel):
    """Plugin Config Here"""
    qzone_handle: ScopedConfig

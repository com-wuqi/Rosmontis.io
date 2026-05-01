from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    _: bool = False


class Config(BaseModel):
    """Plugin Config Here"""
    hooked_mcp: ScopedConfig

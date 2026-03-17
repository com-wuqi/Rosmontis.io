from pydantic import BaseModel

class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    self_tts_api_url: str = ''
    self_ref_audio_path: str = ''
    self_prompt_text: str = ''
    self_prompt_lang: str = ''
    self_text_lang: str = ''

class Config(BaseModel):
    """插件主配置,包含作用域"""
    self_build_tts: ScopedConfig

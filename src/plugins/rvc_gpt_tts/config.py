from pydantic import BaseModel

class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    tts_api_url: str
    ref_audio_path: str
    prompt_text: str
    prompt_lang: str
    text_lang: str

class Config(BaseModel):
    """插件主配置,包含作用域"""
    rvc_gpt_tts: ScopedConfig

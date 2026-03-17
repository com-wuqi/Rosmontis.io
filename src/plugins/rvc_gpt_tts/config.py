from pydantic import BaseModel

class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    gpt_tts_api_url: str
    gpt_ref_audio_path: str
    gpt_prompt_text: str
    gpt_prompt_lang: str
    gpt_text_lang: str

class Config(BaseModel):
    """插件主配置,包含作用域"""
    rvc_gpt_tts: ScopedConfig

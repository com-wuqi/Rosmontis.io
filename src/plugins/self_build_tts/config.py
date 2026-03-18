from pydantic import BaseModel

class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    gpt_sovits_tts_api_url: str = ''
    gpt_sovits_ref_audio_path: str = ''
    gpt_sovits_prompt_text: str = ''
    gpt_sovits_prompt_lang: str = ''
    gpt_sovits_text_lang: str = ''

class Config(BaseModel):
    """插件主配置,包含作用域"""
    self_build_tts: ScopedConfig

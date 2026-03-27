from typing import Literal

from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool
    is_enable_gpt_sovits: bool = False
    is_enable_qwen3_customvoice: bool = False
    is_enable_qwen3_voice_design: bool = False
    is_enable_qwen3_base: bool = False

    gpt_sovits_tts_api_url: str = ''
    gpt_sovits_ref_audio_path: str = ''
    gpt_sovits_prompt_text: str = ''
    gpt_sovits_prompt_lang: str = ''
    gpt_sovits_text_lang: str = ''

    qwen3_tts_customvoice_api_url: str = "http://localhost:8000"
    qwen3_tts_customvoice_lang_disp: Literal[
        'Auto', 'Chinese', 'English', 'German', 'Italian',
        'Portuguese', 'Spanish', 'Japanese', 'Korean',
        'French', 'Russian'] = "Auto"
    qwen3_tts_customvoice_spk_disp: Literal[
        'Serena', 'Vivian', 'Uncle Fu', 'Ryan',
        'Aiden', 'Ono Anna', 'Sohee',
        'Eric', 'Dylan'] = 'Vivian'
    qwen3_tts_customvoice_instruct: str = ""

    qwen3_tts_voice_design_api_url: str = "http://localhost:8000"
    qwen3_tts_voice_design_lang_disp: Literal[
        'Auto', 'Chinese', 'English', 'German', 'Italian',
        'Portuguese', 'Spanish', 'Japanese', 'Korean',
        'French', 'Russian'] = "Auto"
    qwen3_tts_voice_design_design: str = ""

    qwen3_tts_base_api_url: str = "http://localhost:8000"
    # qwen3_tts_base_save_prompt_ref_aud: str = "" 机器人获取
    qwen3_tts_base_use_xvec: bool = False  # 仅用说话人向量，效果有限，但不用传入参考音频文本
    qwen3_tts_base_lang_disp: Literal[
        'Auto', 'Chinese', 'English', 'German', 'Italian',
        'Portuguese', 'Spanish', 'Japanese', 'Korean',
        'French', 'Russian'] = "Auto"  # 仅仅在生成时候需要

class Config(BaseModel):
    """插件主配置,包含作用域"""
    self_build_tts: ScopedConfig

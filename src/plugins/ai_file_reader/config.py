from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool = True
    is_enable_image: bool = False
    image_ai_api_url: str = ""
    image_ai_api_key: str = ""
    image_ai_model_name: str = ""
    image_ai_rate_limit: int = 10  # 每分钟可以读取的图片数目


class Config(BaseModel):
    """Plugin Config Here"""
    ai_file_reader: ScopedConfig

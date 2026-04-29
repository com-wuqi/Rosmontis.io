from pydantic import BaseModel


class ScopedConfig(BaseModel):
    """Plugin Config Here"""
    is_enable: bool = True
    is_enable_image: bool = False
    image_ai_api_url: str = ""
    image_ai_api_key: str = ""
    image_ai_model_name: str = ""
    image_ai_api_timeout: int = 180  # api 超时限制
    image_ai_rate_limit: int = 10  # 每秒钟可以读取的图片数目
    image_zip_quality: int = 85  # 质量 用于有损格式 (JPEG/WebP)
    image_zip_lossless: bool = False  # PNG/WebP 无损模式
    # 等比缩放，使用一个参数即可
    image_zip_max_width: int | None = None  # 等比缩放，最大宽度
    image_zip_max_height: int | None = None  # 等比缩放，最大高度


class Config(BaseModel):
    """Plugin Config Here"""
    ai_file_reader: ScopedConfig

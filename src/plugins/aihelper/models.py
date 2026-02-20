from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, Float, Boolean
from nonebot import require
require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model

class Settings(Model):
    __tablename__ = "aihelper_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    url: Mapped[String] = mapped_column(String(255),nullable=False)
    api_key: Mapped[String] = mapped_column(String(255),nullable=False)
    model_name: Mapped[String] = mapped_column(String(255),nullable=False)
    max_length: Mapped[int] = mapped_column(Integer,nullable=False,default=15)
    # 组对话后压缩
    system: Mapped[str] = mapped_column(Text)
    # 系统提示词
    temperature: Mapped[float] = mapped_column(Float,nullable=False,default=1.0)
    # 增加温度
    is_enabled: Mapped[bool] = mapped_column(Boolean,nullable=False,default=False)
    # 默认不启用, 对 id=1 无效

class AIHelperComments(Model):
    __tablename__ = "aihelper_comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[int] = mapped_column(Integer,nullable=False,index=True,unique=True)
    # 区分不同用户
    message: Mapped[str] = mapped_column(Text)



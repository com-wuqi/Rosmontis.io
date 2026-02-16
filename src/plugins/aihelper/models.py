from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Float
from typing import Optional, List
from datetime import datetime
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
    max_length: Mapped[int] = mapped_column(Integer,nullable=False,default=60)
    # 60 组对话后压缩


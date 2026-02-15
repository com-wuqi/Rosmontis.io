from typing import List

from pydantic import BaseModel
from typing import List

class Config(BaseModel):
    """Plugin Config Here"""
    is_enable: bool = True
    is_debug: bool = True
    is_use_cache: bool = True
    cache_timeout: int = 90 # 单位 秒
    cache_length_limit: int = 100
    is_allow_group: bool = True
    # 群聊
    is_allow_user: bool = True
    # 私聊
    max_size: int = 5
    # 最大单次总数

    is_enable_whitelist: bool = False
    is_enable_whitelist_group: bool = False
    is_enable_whitelist_user: bool = False
    whitelist_groups: List[int] = []
    whitelist_users: List[int] = []

    is_enable_blacklist: bool = False
    is_enable_blacklist_group: bool = False
    is_enable_blacklist_user: bool = False
    blacklist_groups: List[int] = []
    blacklist_users: List[int] = []



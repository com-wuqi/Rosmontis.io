from typing import Callable, Dict, Any

from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="hooked_mcp_tools",
    description="",
    usage="",
    config=Config,
)

_config = get_plugin_config(Config)
config = _config.hooked_mcp


async def hooked_mcp_test():
    return True


hooked_functions: Dict[str, Callable] = {"hooked_mcp_test": hooked_mcp_test}  # 工具名称:函数
hooked_tools: list[dict[str, str | dict[str, str | dict[Any, Any] | bool]]] = [{
    "type": "function",
    "function": {
        "name": "hooked_mcp_test",
        "description": f"测试 基于插件的mcp",
        "parameters": {},
        "additionalProperties": False
    }
}]
# [{
#     "type": "function",
#     "function": {
#         "name": prefixed_name,
#         "description": f"[{original_name}] {tool.description}",
#         "parameters": tool.inputSchema
#     }
# },...]

from dataclasses import dataclass
from typing import Optional, Dict, Literal


@dataclass
class McpServerConfig:
    """MCP 服务器配置"""
    name: str  # 唯一, 必须
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    # 通信方案

    # stdio config
    command: Optional[str] = None  # 必须
    args: Optional[list] = None
    env: Optional[Dict[str, str]] = None

    # SSE / Streamable HTTP config
    url: Optional[str] = None  # 必须

    # 通用配置
    timeout: int = 60  # 可选, client 超时控制
    prefix: Optional[str] = None
    # 私有前缀, 用于区分同名工具
    headers: Optional[Dict[str, str]] = None  # 认证头等


# 以下是配置项
mcp_init_timeout = 180  # 初始化时间限制 (加载工具列表前)
mcp_configs = [
    McpServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./mcp_workdir/fs"],
        prefix="fs",
    ),
    McpServerConfig(
        name="rosmontis_mcp",
        transport="stdio",
        command="python",
        args=["./src/plugins/mcp_support/buildin_mcp.py"],
        env={
            "WEBSEARCH_BASE_URL": "https://api.bocha.cn/v1/web-search",
            # 网页搜索 api ,不支持修改, https://open.bochaai.com/ 注册
            "WEBSEARCH_TIMEOUT": "90",
            # 单次搜索超时
            "WEBSEARCH_API_KEY": "sk-",
            # https://open.bochaai.com/ 注册,
            "E2B_API_URL": "",
            # 云沙箱(py3代码执行) https://e2b.dev/ 注册
            "E2B_API_KEY": "e2b_",
            # https://e2b.dev/ 注册
        },
        prefix="ros",
    ),
]
"""
其他例子
    McpServerConfig(
        name="local_python",
        transport="stdio",
        command="python",
        args=["/path/to/local_mcp_server.py"],
        env={"API_KEY": "secret_123"},
        prefix="local",
    )
    McpServerConfig(
        name="database",
        transport="streamable-http",
        url="http://internal:9000/mcp",
        prefix="db",
        headers={"X-API-Key": "secret"}
    )
    McpServerConfig(
        name="search",
        transport="sse",
        url="http://internal:8080/sse",
        prefix="search",
    )
"""

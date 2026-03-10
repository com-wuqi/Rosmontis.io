import time

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rosmontis_mcp")


@mcp.tool()
def get_current_time():
    """
    获取当前的系统时间
    :return: 时间字符串, 格式为：YYYY-MM-DD HH:MM:SS
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


if __name__ == "__main__":
    mcp.run(transport="stdio")

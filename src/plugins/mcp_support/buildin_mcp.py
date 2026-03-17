import os
from typing import Dict

import httpx
from e2b_code_interpreter import AsyncSandbox
from mcp.server.fastmcp import FastMCP

from buildin_mcp_share import *

mcp = FastMCP("rosmontis_mcp")
env_dict = dict(os.environ)

dir_list = [os.path.abspath("mcp_workdir/fs"), os.path.abspath("mcp_workdir/memory")]
for dir_1 in dir_list:
    os.makedirs(dir_1, exist_ok=True)

def get_current_time():
    """
    获取当前的系统时间
    :return: 时间字符串, 格式为：YYYY-MM-DD HH:MM:SS
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())



async def call_web_search(
        query: str,
        freshness: str,
        summary: bool = True,
        count: int = 10,
) -> Dict:
    """
    异步调用 Web Search API（兼容 httpx）

    Args:
        query: 搜索关键词
        summary: 是否返回摘要（默认 True）
        count: 返回结果数量（默认 10）
        freshness: 搜索指定时间范围内的网页 [noLimit,oneDay,oneWeek,oneMonth,oneYear]

    Returns:
        dict，若出错则包含 error 字段, 成功为 success 字段
    """
    timeout: float = float(env_dict["WEBSEARCH_TIMEOUT"])
    headers = {
        "Authorization": f"Bearer {env_dict['WEBSEARCH_API_KEY']}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "summary": summary,
        "count": count,
        "freshness": freshness,
    }
    bucket_websearch = get_bucket_websearch()
    semaphore_websearch = get_websearch_semaphore()

    await bucket_websearch.acquire()
    async with semaphore_websearch:
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    env_dict["WEBSEARCH_BASE_URL"],
                    headers=headers,
                    json=payload  # httpx 会自动序列化字典为 JSON
                )
                response.raise_for_status()
                raw_data = response.json()
                data = {}
                _ids = 0
                for d in raw_data['data']["webPages"]["value"]:
                    # 数据清洗, 字段更易于阅读
                    data[_ids] = f"标题: {d['name']}\n, url: {d['url']}, 总结: {d['summary']}"
                    _ids += 1

                return {"success": data}
            except httpx.TimeoutException:
                return {"error": "请求超时"}
            except httpx.HTTPStatusError as e:
                return {"error": f"HTTP 错误 {e.response.status_code}: {e.response.text}"}
            except KeyError as e:
                return {"error": f"keyError: {e}"}
            except Exception as e:
                return {"error": f"请求异常: {str(e)}"}


async def run_code_in_e2b(code: str, requirements: list[str], timeout: int = 120):
    """
    通过单次调用来执行 Python 代码, 使用 print 获得返回值
    :param code: 单次调用所需要执行的代码
    :param requirements: 每次都需要安装, 运行代码需要安装的包列表，例如 [\"numpy\", \"pandas\"]
    :param timeout: 容器的有效期, 单位秒, 最长3600秒, 默认120秒
    :return: str, 运行输出或报错
    """
    bucket_e2b = get_bucket_e2b()
    semaphore_e2b = get_semaphore_e2b()

    await bucket_e2b.acquire()
    async with semaphore_e2b:
        try:
            if env_dict.get("E2B_API_URL"):
                sandbox = await asyncio.wait_for(
                    AsyncSandbox.create(api_key=env_dict["E2B_API_KEY"], api_url=env_dict["E2B_API_URL"],
                                        timeout=timeout),
                    timeout=60)
            else:
                sandbox = await asyncio.wait_for(
                    AsyncSandbox.create(api_key=env_dict["E2B_API_KEY"], timeout=timeout),
                    timeout=60)
        except asyncio.TimeoutError as e:
            return f"fail to create sandbox: TimeoutError: {e}"

        except Exception as e:
            return f"fail to create sandbox: Exception: {e}"

        if len(requirements) != 0:
            cmds = f"pip install {' '.join(requirements)}"
            await sandbox.commands.run(cmds, timeout=timeout)

        exec_codes = await sandbox.run_code(code)
        await sandbox.kill()
        return exec_codes.logs.stdout

if __name__ == "__main__":

    is_enable_get_current_time = env_dict.get("IS_ENABLE_GET_CURRENT_TIME", "false")
    is_enable_call_web_search = env_dict.get("IS_ENABLE_CALL_WEB_SEARCH", "false")
    is_enable_run_code_in_e2b = env_dict.get("IS_ENABLE_RUN_CODE_IN_E2B", "false")

    if is_enable_get_current_time == "true":
        mcp.add_tool(get_current_time)
    if is_enable_call_web_search == "true":
        if env_dict.get("WEBSEARCH_BASE_URL") and env_dict.get("WEBSEARCH_TIMEOUT") and env_dict.get(
                "WEBSEARCH_API_KEY"):
            mcp.add_tool(call_web_search)
        else:
            pass
    if is_enable_run_code_in_e2b == "true":
        if env_dict.get("E2B_API_KEY"):
            mcp.add_tool(run_code_in_e2b)
        else:
            pass

    mcp.run(transport="stdio")

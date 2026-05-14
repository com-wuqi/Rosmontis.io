from typing import Dict, Any, Tuple

import chromadb
import httpx
from chromadb.api.models.AsyncCollection import AsyncCollection
from e2b_code_interpreter import AsyncSandbox, SandboxLifecycle, SandboxState
from mcp.server.fastmcp import FastMCP, Context

from buildin_mcp_share import *
from knowledge_tools import *

env_dict = dict(os.environ)

dir_list = [os.path.abspath("mcp_workdir/fs"), os.path.abspath("mcp_workdir/memory")]
file_list = [env_dict.get("knowledge_db_fir", "./test_knowledge.db")]
for dir_1 in dir_list:
    os.makedirs(dir_1, exist_ok=True)
for file_1 in file_list:
    if not os.path.exists(file_1):
        pass

mcp = FastMCP("rosmontis_mcp")


def init_chromadb_client() -> Tuple[Any, chromadb.api.models.Collection.Collection]:
    chroma_client = chromadb.PersistentClient(path=env_dict.get("knowledge_db_fir", "./test_knowledge.db"))
    collection = chroma_client.get_or_create_collection(
        name="local_knowledge_base",
        metadata={"hnsw:space": "cosine"},  # 使用余弦相似度，更适合 OpenAI 嵌入
        embedding_function=None
    )
    return chroma_client, collection


_user_sandboxs: Dict[int, Any | None] = {}
_sandbox_locks: Dict[int, asyncio.Lock] = {}

_e2b_init_code = """
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

def _configure_font():
    font_path = '/tmp/SimHei.ttf'
    if not os.path.exists(font_path):
        try:
            os.system('curl -s -L -o /tmp/SimHei.ttf https://github.com/StellarCN/scp_zh/raw/master/fonts/SimHei.ttf')
        except: pass

    if os.path.exists(font_path):
        try:
            fm.fontManager.addfont(font_path)
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False
        except: pass

try:
    _configure_font()
except: pass
"""


def get_sandbox_lock(user_id: int) -> asyncio.Lock:
    """获取或创建指定 sandbox 的锁"""
    if user_id not in _sandbox_locks:
        _sandbox_locks[user_id] = asyncio.Lock()
    return _sandbox_locks[user_id]


def knowledge_sync_from_json(collection: chromadb.api.models.Collection.Collection):
    # use raw_jsons
    get_from_collection = collection.get()
    collection_ids = set(get_from_collection["ids"])
    json_ids = set()
    file_jsons = {}  # 混合不同文件的json, key:id value:json
    for file_items in raw_jsons:
        for items in file_items:
            if items.get("enabled", True) and items.get("id", False):
                json_ids.add(items.get("id"))
                file_jsons[items.get("id")] = items

    to_delete = collection_ids - json_ids
    if to_delete:
        collection.delete(ids=list(to_delete))

    to_add = json_ids - collection_ids
    to_add_ids = []
    to_add_texts = []
    to_add_metadata = []
    if to_add:
        for a_id in list(to_add):
            to_add_ids.append(a_id)
            to_add_texts.append(file_jsons[a_id]["text"])
            to_add_metadata.append(file_jsons[a_id]["metadata"])
        to_add_embeddings = asyncio.run(
            get_all_embedding(sem=1, txt_list=to_add_texts, url=env_dict.get("KNOWLEDGE_API_URL"),
                              key=env_dict.get("KNOWLEDGE_API_TOKEN"),
                              model_name=env_dict.get("KNOWLEDGE_API_MODEL_NAME"),
                              timeout=env_dict.get("KNOWLEDGE_API_TIMEOUT"))
        )
        collection.upsert(ids=to_add_ids, documents=to_add_texts, embeddings=to_add_embeddings)
    else:
        pass


async def get_knowledge(
        collection: chromadb.api.models.Collection.Collection,
        ctx: Context,
        query: str,
        counts: int = 2) -> List[str]:
    query_embedding = await get_embedding(
        sem=1, txt=query,
        url=env_dict.get("KNOWLEDGE_API_URL"), key=env_dict.get("KNOWLEDGE_API_TOKEN"),
        model_name=env_dict.get("KNOWLEDGE_API_MODEL_NAME"), timeout=env_dict.get("KNOWLEDGE_API_TIMEOUT")
    )
    results = collection.query(query_embeddings=[query_embedding], n_results=counts)
    # 文件保存的向量化数据，同步，不支持异步查询
    documents = results['documents'][0]
    await ctx.debug(f"get_knowledge: {documents}")
    return documents


async def get_sandbox(ctx: Context, user_id: int, timeout: int = 86_400) -> Any | None | str:
    if user_id in _user_sandboxs:
        sbx_info = await _user_sandboxs[user_id].get_info()
        if sbx_info.state in [SandboxState.PAUSED, SandboxState.RUNNING]:
            return _user_sandboxs[user_id]
        else:
            pass
            await ctx.debug(f"sandbox user {user_id} is not running: {_user_sandboxs[user_id].get_info().state}")
    else:
        await ctx.debug(f"sandbox user {user_id} is not in dict")
    try:
        sandbox = await asyncio.wait_for(
            AsyncSandbox.create(
                api_key=env_dict["E2B_API_KEY"],
                api_url=env_dict["E2B_API_URL"] if env_dict.get("E2B_API_URL") else None,
                timeout=timeout,
                lifecycle=SandboxLifecycle(on_timeout="pause", auto_resume=True)
            ),
            timeout=60)
    except asyncio.TimeoutError as e1:
        await ctx.debug(f"fail to create sandbox: TimeoutError: {e1}")
        return f"fail to create sandbox: TimeoutError: {e1}"

    except Exception as e1:
        await ctx.debug(f"fail to create sandbox: Exception: {e1}")
        return f"fail to create sandbox: Exception: {e1}"

    _user_sandboxs[user_id] = sandbox
    return _user_sandboxs[user_id]


async def get_current_time(ctx: Context):
    """
    获取当前的系统时间
    :return: 时间字符串, 格式为：YYYY-MM-DD HH:MM:SS
    """
    await ctx.debug("bulidin_mcp: get_current_time")
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


async def call_web_search(
        ctx: Context,
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
                await ctx.debug(str({"error": "请求超时"}))
                return {"error": "请求超时"}
            except httpx.HTTPStatusError as e:
                await ctx.debug(str({"error": f"HTTP 错误 {e.response.status_code}: {e.response.text}"}))
                return {"error": f"HTTP 错误 {e.response.status_code}: {e.response.text}"}
            except KeyError as e:
                await ctx.debug(str({"error": f"keyError: {e}"}))
                return {"error": f"keyError: {e}"}
            except Exception as e:
                await ctx.debug(str({"error": f"请求异常: {str(e)}"}))
                return {"error": f"请求异常: {str(e)}"}


async def run_code_in_e2b(ctx: Context, user_id: int, code: str, requirements: list[str], timeout: int = 300):
    """
    通过单次调用来执行 Python 代码, 使用 print 获得返回值,
    生成的文件不可直接打开，保存并 获取目录（print），然后获取 url
    :param user_id: int, 在信息的第一个冒号前提供, 按原样传递
    :param code: 单次调用所需要执行的代码
    :param requirements: 每次都需要安装, 运行代码需要安装的包列表，例如 [\"numpy\", \"pandas\"]
    :param timeout: 容器的有效期, 单位秒, 最长3600秒, 默认300秒
    :return: {"stdout":stdout, "stderr":stderr} | {"fail":msg}
    """
    bucket_e2b = get_bucket_e2b()
    semaphore_e2b = get_semaphore_e2b()
    _res = {}

    await bucket_e2b.acquire()
    async with semaphore_e2b:

        _lock = get_sandbox_lock(user_id=user_id)
        async with _lock:
            sandbox = await get_sandbox(user_id=user_id, timeout=timeout, ctx=ctx)
            if type(sandbox) == str:
                return {"fail": sandbox}

            if len(requirements) != 0:
                cmds = f"pip install {' '.join(requirements)}"
                await sandbox.commands.run(cmds, timeout=timeout)

            _codes = _e2b_init_code + "\n" + code
            exec_codes = await sandbox.run_code(_codes)
            return {"stdout": exec_codes.logs.stdout, "stderr": exec_codes.logs.stderr}


async def e2b_get_file(ctx: Context, user_id: int, path: str, file_timeout: int = 120):
    """
    根据 user_id 和 目录， 从E2B沙箱获取文件 url
    :param file_timeout: 链接有效期， 默认 120 秒
    :param user_id: int, 在信息的第一个冒号前提供, 按原样传递
    :param path: str, 文件的path
    :return: 文件 url
    """
    bucket_e2b = get_bucket_e2b()
    semaphore_e2b = get_semaphore_e2b()

    await bucket_e2b.acquire()
    async with semaphore_e2b:
        _lock = get_sandbox_lock(user_id=user_id)
        async with _lock:
            sandbox = await get_sandbox(user_id=user_id, ctx=ctx)
            signed_url = sandbox.download_url(path=path, use_signature_expiration=file_timeout)
            return signed_url


if __name__ == "__main__":
    try:
        is_enable_get_current_time = env_dict.get("IS_ENABLE_GET_CURRENT_TIME", "false")
        is_enable_call_web_search = env_dict.get("IS_ENABLE_CALL_WEB_SEARCH", "false")
        is_enable_run_code_in_e2b = env_dict.get("IS_ENABLE_RUN_CODE_IN_E2B", "false")
        is_enable_knowledge = env_dict.get("IS_ENABLE_KNOWLEDGE", "false")

        if is_enable_get_current_time == "true":
            mcp.add_tool(get_current_time)
        if is_enable_call_web_search == "true":
            if (env_dict.get("WEBSEARCH_BASE_URL")
                    and env_dict.get("WEBSEARCH_TIMEOUT")
                    and env_dict.get("WEBSEARCH_API_KEY")):
                mcp.add_tool(call_web_search)
            else:
                pass
        if is_enable_run_code_in_e2b == "true":
            if env_dict.get("E2B_API_KEY"):
                mcp.add_tool(run_code_in_e2b)
                mcp.add_tool(e2b_get_file)
            else:
                pass
        if is_enable_knowledge:
            if (env_dict.get("KNOWLEDGE_API_URL")
                    and env_dict.get("KNOWLEDGE_API_TOKEN")
                    and env_dict.get("KNOWLEDGE_API_MODEL_NAME")
                    and env_dict.get("KNOWLEDGE_API_TIMEOUT")):
                _chroma_client, _collection = init_chromadb_client()
                knowledge_sync_from_json(collection=_collection)


                async def get_knowledge_tool(
                        ctx: Context,
                        query: str,
                        counts: int = 2
                ) -> List[str]:
                    """
                    查询知识
                    Args:
                        query: 搜索关键词或者关键句
                        counts: 返回相关的条目个数
                    Returns:
                        list, 最相关的条目
                    """
                    return await get_knowledge(
                        collection=_collection,
                        ctx=ctx,
                        query=query,
                        counts=counts
                    )


                mcp.add_tool(get_knowledge_tool)
            else:
                pass

        mcp.run(transport="stdio")
    except (KeyboardInterrupt, Exception) as e:
        import traceback

        traceback.print_exc()
        for sbx in _user_sandboxs.values():
            try:
                sbx.close()
            except Exception as e:
                traceback.print_exc()

# async def init_chromadb_client() -> Tuple[Any, chromadb.api.models.AsyncCollection.AsyncCollection]:
#     chroma_client = await chromadb.AsyncClientCreator.create(
#         settings=Settings(
#             is_persistent = True,
#             persist_directory=env_dict.get("knowledge_db_fir", "./test_knowledge.db")
#         )
#     )
#
#     collection = await chroma_client.get_or_create_collection(
#         name="local_knowledge_base",
#         metadata={"hnsw:space": "cosine"}  # 使用余弦相似度，更适合 OpenAI 嵌入
#     )
#     return chroma_client, collection

# async def knowledge_sync_from_json(collection: chromadb.api.models.AsyncCollection.AsyncCollection):
#     # use raw_jsons
#     get_from_collection = await collection.get()
#     collection_ids = set(get_from_collection["ids"])
#     json_ids = set()
#     file_jsons = {}  # 混合不同文件的json, key:id value:json
#     for file_items in raw_jsons:
#         for items in file_items:
#             if items.get("enabled", True) and items.get("id", False):
#                 json_ids.add(items.get("id"))
#                 file_jsons[items.get("id")] = items
#
#     to_delete = collection_ids - json_ids
#     if to_delete:
#         await collection.delete(ids=list(to_delete))
#
#     to_add = json_ids - collection_ids
#     to_add_ids = []
#     to_add_texts = []
#     to_add_metadata = []
#     if to_add:
#         for a_id in list(to_add):
#             to_add_ids.append(a_id)
#             to_add_texts.append(file_jsons[a_id]["text"])
#             to_add_metadata.append(file_jsons[a_id]["metadata"])
#     to_add_embeddings = await get_all_embedding(
#         sems=1, txt_list=to_add_texts,
#         url=env_dict.get("KNOWLEDGE_API_URL"), key=env_dict.get("KNOWLEDGE_API_TOKEN"),
#         model_name=env_dict.get("KNOWLEDGE_API_MODEL_NAME"), timeout=env_dict.get("KNOWLEDGE_API_TIMEOUT"))
#     await collection.upsert(ids=to_add_ids, documents=to_add_texts, embeddings=to_add_embeddings)

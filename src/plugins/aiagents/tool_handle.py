import json

from .tool_funcs import *


async def handle_web_search(tool_call) -> dict:
    args = json.loads(tool_call.function.arguments)
    query = args.get("query")
    if not query:
        return {}
    freshness = args.get("freshness", "noLimit")
    count = args.get("count", 10)
    _searched = await call_web_search(query=query, freshness=freshness, count=count)
    return _searched


async def handle_e2b_sandbox(tool_call) -> str:
    args = json.loads(tool_call.function.arguments)
    code: str = args.get("code")
    if not code:
        return ""
    logger.debug(f"e2b_sandbox codes: {code}")
    timeout: int = args.get("timeout", 120)
    requirements: list[str] = args.get("requirements", [])
    _res = await run_code_in_e2b(code, timeout=timeout, requirements=requirements)
    if _res == -1:
        return ""
    return _res

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

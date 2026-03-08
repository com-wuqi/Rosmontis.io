def get_dict_by_name(name: str) -> dict:
    web_search = {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "当用户需要查询实时新闻、最新事件、具体数据或知识库中没有的信息时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，需要精简且准确，例如 '2024 年巴黎奥运会金牌榜'"
                    },
                    "freshness": {
                        "type": "string",
                        "enum": ["noLimit", "oneDay", "oneWeek", "oneMonth", "oneYear"],
                        "description": "时间范围，默认 noLimit。如果用户问'今天'或'最新'，用 oneDay",
                        "default": "noLimit"
                    },
                    "count": {
                        "type": "integer",
                        "description": "返回结果数量，1-50，最大单次搜索返回50条",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    }
    e2b_sandbox = {
        "type": "function",
        "function": {
            "name": "e2b_code",
            "description": "通过单次调用来执行 Python 代码, 使用 print 获得返回值",
            "parameters": {
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "每次都需要安装, 运行代码需要安装的包列表，例如 [\"numpy\", \"pandas\"]"
                    },
                    "code": {
                        "type": "string",
                        "description": "单次调用所需要执行的代码"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "容器的有效期, 单位秒, 最长3600秒, 默认120秒",
                        "minimum": 1,
                        "maximum": 3600,
                        "default": 120

                    }
                },
                "required": ["code"]
            }
        }
    }
    get_time_tool = {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的系统时间（例如：2025-03-07 14:30:00）",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
    if name == "WEB_SEARCH_TOOL":
        return web_search
    elif name == "E2B_SANDBOX_TOOL":
        return e2b_sandbox
    elif name == "GET_TIME_TOOL":
        return get_time_tool
    else:
        return {}


WEB_SEARCH_TOOL = {
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
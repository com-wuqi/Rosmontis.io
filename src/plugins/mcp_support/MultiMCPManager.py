import asyncio
from contextlib import AbstractAsyncContextManager
from typing import Dict, Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from nonebot.log import logger

from .mcp_config import McpServerConfig, mcp_init_timeout


class MultiMCPManager:
    def __init__(self, configs: list[McpServerConfig]):
        self.configs = configs  # 配置
        self.sessions: Dict[str, ClientSession] = {}  # 保存会话
        self.tool_map: Dict[str, str] = {}  # 修正名称: MCP服务名
        self.tool_original_map: Dict[str, str] = {}  # 修饰后的名称-原工具名
        self.all_tools: list = []  # 工具的列表
        self._tasks: list[asyncio.Task] = []  # 后台任务列表
        self._stop_event = asyncio.Event()  # 关闭事件
        self._ready_events: Dict[str, asyncio.Event] = {}  # 事件就绪列表: 初始化时创建

    async def connect_all(self):
        """ 初始化所有mcp连接 """
        self._stop_event.clear()
        self._ready_events.clear()

        for cfg in self.configs:
            self._ready_events[cfg.name] = asyncio.Event()  # 插入事件
            task = asyncio.create_task(self._run_server(cfg))
            self._tasks.append(task)

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    *[ev.wait() for ev in self._ready_events.values()]
                ),
                timeout=mcp_init_timeout
            )
            logger.info("All MCP servers ready")
        except asyncio.TimeoutError:
            not_ready = [name for name, ev in self._ready_events.items() if not ev.is_set()]
            logger.warning(f"connect_all TimeoutError: MCP servers ready within : {not_ready}")

        except Exception as e:
            logger.warning(f"connect_all Failed: {e}")

        await self.refresh_tools()

    async def _run_server(self, cfg: McpServerConfig):

        transport = None
        transport_entered = False
        session = None
        session_entered = False

        try:
            transport = await self._create_transport(cfg)
            read, write = await transport.__aenter__()
            transport_entered = True

            session = ClientSession(read, write)
            await session.__aenter__()
            session_entered = True
            await session.initialize()

            self.sessions[cfg.name] = session
            self._ready_events[cfg.name].set()  # 标记为初始化完成
            logger.info(f"Server: {cfg.name} inited")

            await self._stop_event.wait()  # 等待停止事件

        except asyncio.CancelledError:
            logger.info(f"Server: {cfg.name} task cancelled")
            raise

        except Exception as e:
            logger.warning(f"Server: {cfg.name} init failed: {e}")
            raise

        finally:
            if session_entered:
                try:
                    await session.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"session: {cfg.name} __aexit__ failed: {e}")
            self.sessions.pop(cfg.name, None)
            if transport_entered:
                try:
                    await transport.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"transport: {cfg.name} __aexit__ failed: {e}")
            logger.info(f"Server: {cfg.name} finished")

    @staticmethod
    async def _create_transport(cfg: McpServerConfig) -> AbstractAsyncContextManager:
        """ 根据配置创建对应的 transport """
        if cfg.transport == "stdio":
            if not cfg.command:
                raise ValueError(f"stdio '{cfg.name}'need command")
            server_params = StdioServerParameters(
                command=cfg.command,
                args=cfg.args or [],
                env=cfg.env
            )
            return stdio_client(server_params)
        elif cfg.transport == "sse":
            if not cfg.url:
                raise ValueError(f"sse '{cfg.name}'need url")
            return sse_client(cfg.url, timeout=cfg.timeout)
        elif cfg.transport == "streamable-http":
            if not cfg.url:
                raise ValueError(f"streamable-http '{cfg.name}'need url")
            return streamable_http_client(
                url=cfg.url,
                timeout=cfg.timeout,
                headers=cfg.headers or {}
            )
        else:
            raise ValueError(f"transport {cfg.transport} not supported")


    def _reset_tool_data(self):
        self.all_tools.clear()
        self.tool_map.clear()
        self.tool_original_map.clear()

    async def refresh_tools(self):
        """ 获取全部工具, 维护映射 """
        self._reset_tool_data()
        for name, session in self.sessions.items():
            # name: MCP 名称
            cfg = next((c for c in self.configs if c.name == name), None)
            prefix = cfg.prefix if cfg else name
            try:
                tools_response = await session.list_tools()
                for tool in tools_response.tools:
                    original_name = tool.name  # 原始名称
                    prefixed_name = f"{prefix}_{original_name}"  #
                    if prefixed_name in self.tool_map:
                        logger.warning(f"tool {prefixed_name} already used")
                        prefixed_name = f"{name}_{prefix}_{original_name}"

                    self.tool_original_map[prefixed_name] = original_name
                    # 修正名称: 原始名称
                    self.tool_map[prefixed_name] = name
                    # 修正名称: MCP服务名

                    self.all_tools.append({
                        "type": "function",
                        "function": {
                            "name": prefixed_name,
                            "description": f"[{original_name}] {tool.description}",
                            "parameters": tool.inputSchema
                        }
                    })
                    logger.debug(f"tool: {prefixed_name} added")

            except Exception as e:
                logger.warning(f"server: {name} failed to get tools: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """ 调用工具 """
        server_name = self.tool_map.get(tool_name)
        original_name = self.tool_original_map.get(tool_name)
        if server_name is None or original_name is None:
            raise ValueError(f"tool {tool_name} not registered")

        logger.debug(f"tool: {server_name} : {original_name} called")
        session = self.sessions[server_name]  # 获取 ClientSession

        _text = ""
        result = await session.call_tool(name=original_name, arguments=arguments)
        if hasattr(result, 'content') and result.content:
            _text = "\n".join(
                item.text if hasattr(item, 'text') else str(item)
                for item in result.content
            )
        return _text or "执行成功但无输出"

    async def close_all(self):
        """ 关闭所有连接 """
        self._stop_event.set()  # 触发关闭事件
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._stop_event.clear()
        self.sessions.clear()
        self._reset_tool_data()

    def get_status(self) -> Dict[str, Any]:
        """ MCP 状态 """
        return {
            "connected_servers": list(self.sessions.keys()),
            "all_tools": len(self.tool_map),
            "transport_summary": {
                cfg.name: cfg.transport for cfg in self.configs
            }
        }

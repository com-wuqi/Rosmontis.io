#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OneBot 文件流上传服务器模拟实现（带 Token 认证）
支持 upload_file_stream 分片上传，最后合并文件并返回路径
基于 WebSocket 协议
"""

import asyncio
import base64
import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Set

import websockets
from websockets.http import Headers
from websockets.server import WebSocketServerProtocol

# ========== 配置区域 ==========
HOST = "0.0.0.0"  # 监听地址
PORT = 6011  # 监听端口
UPLOAD_DIR = Path("./uploads")  # 文件保存根目录
TEMP_DIR = Path("./temp_streams")  # 临时分片存储目录
CLEANUP_INTERVAL = 300  # 清理间隔（秒）
STREAM_TIMEOUT = 600  # 流超时时间（秒）

# 认证 Token（若为空字符串则跳过认证）
TOKEN = "your_secret_token_here"  # 请替换为实际 Token，或从环境变量读取
# TOKEN = os.environ.get("NAPCAT_TOKEN", "")  # 也可以从环境变量读取

# =============================

# 确保目录存在
UPLOAD_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)


class StreamState:
    """单个上传流的状态"""

    def __init__(
            self,
            stream_id: str,
            total_chunks: int,
            file_size: int,
            expected_sha256: str,
            filename: str,
            file_retention: int,
    ):
        self.stream_id = stream_id
        self.total_chunks = total_chunks
        self.file_size = file_size
        self.expected_sha256 = expected_sha256.lower()
        self.filename = filename
        self.file_retention = file_retention  # 保留时间（毫秒），暂未使用
        self.received_chunks: Set[int] = set()  # 已接收的分片索引
        self.temp_dir = TEMP_DIR / stream_id
        self.temp_dir.mkdir(exist_ok=True)
        self.last_active = time.time()
        self.completed = False
        self.final_path: Optional[Path] = None

    def is_complete(self) -> bool:
        """是否已收到所有分片"""
        return len(self.received_chunks) == self.total_chunks

    def add_chunk(self, index: int, data: bytes) -> bool:
        """保存分片，返回是否成功（新分片）"""
        if index in self.received_chunks:
            return False  # 重复分片
        chunk_path = self.temp_dir / f"chunk_{index:06d}.part"
        with open(chunk_path, "wb") as f:
            f.write(data)
        self.received_chunks.add(index)
        self.last_active = time.time()
        return True

    def assemble_file(self) -> Path:
        """合并所有分片，验证 SHA256，返回最终文件路径"""
        # 按索引顺序合并
        final_filename = f"{uuid.uuid4().hex}_{self.filename}"
        final_path = UPLOAD_DIR / final_filename
        hasher = hashlib.sha256()
        with open(final_path, "wb") as out_f:
            for i in range(self.total_chunks):
                chunk_path = self.temp_dir / f"chunk_{i:06d}.part"
                if not chunk_path.exists():
                    raise RuntimeError(f"缺失分片 {i}")
                with open(chunk_path, "rb") as in_f:
                    data = in_f.read()
                    out_f.write(data)
                    hasher.update(data)
        # 验证 SHA256
        actual_sha256 = hasher.hexdigest()
        if actual_sha256 != self.expected_sha256:
            # 删除错误文件
            final_path.unlink()
            raise ValueError(
                f"SHA256 不匹配，期望 {self.expected_sha256}，实际 {actual_sha256}"
            )
        # 清理临时目录
        shutil.rmtree(self.temp_dir)
        self.completed = True
        self.final_path = final_path
        return final_path

    def cleanup(self):
        """清理临时文件（用于超时）"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.completed = True  # 标记为已完成（失败）避免后续操作


class UploadServer:
    def __init__(self, token: str = ""):
        self.token = token
        self.streams: Dict[str, StreamState] = {}
        self.lock = asyncio.Lock()  # 保护 streams 字典
        self.cleanup_task: Optional[asyncio.Task] = None

    async def authenticate(self, headers: Headers) -> bool:
        """
        验证客户端认证头
        支持 Bearer Token 格式
        """
        if not self.token:  # 未配置 Token 则跳过认证
            return True

        auth_header = headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False

        token = auth_header[7:]  # 去掉 "Bearer " 前缀
        return token == self.token

    async def start_cleanup(self):
        """启动后台清理任务"""
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL)
            await self._cleanup_stale_streams()

    async def _cleanup_stale_streams(self):
        """清理超时的未完成流"""
        now = time.time()
        async with self.lock:
            to_delete = []
            for sid, state in self.streams.items():
                if not state.completed and now - state.last_active > STREAM_TIMEOUT:
                    state.cleanup()
                    to_delete.append(sid)
            for sid in to_delete:
                del self.streams[sid]
            if to_delete:
                print(f"清理了 {len(to_delete)} 个超时流")

    async def handle_connection(self, websocket: WebSocketServerProtocol):
        """处理单个 WebSocket 连接（含认证）"""
        # 认证检查
        if not await self.authenticate(websocket.request_headers):
            await websocket.close(
                code=1008, reason="Unauthorized: Invalid or missing token"
            )
            print(f"来自 {websocket.remote_address} 的连接认证失败")
            return

        print(f"认证成功，客户端 {websocket.remote_address} 已连接")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    await self.send_error(
                        websocket,
                        "无效的 JSON",
                        echo=data.get("echo") if isinstance(data, dict) else None,
                    )
                    continue

                action = data.get("action")
                params = data.get("params", {})
                echo = data.get("echo")

                if action == "upload_file_stream":
                    await self.handle_upload_file_stream(websocket, params, echo)
                else:
                    await self.send_error(
                        websocket, f"不支持的动作: {action}", echo=echo
                    )
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            print(f"客户端 {websocket.remote_address} 断开连接")
            # 连接关闭时不需要立即清理流，等待超时即可

    async def handle_upload_file_stream(self, websocket, params: dict, echo: str):
        """处理 upload_file_stream 请求"""
        stream_id = params.get("stream_id")
        if not stream_id:
            return await self.send_error(websocket, "缺少 stream_id", echo=echo)

        # 检查是否完成信号
        is_complete = params.get("is_complete", False)

        if is_complete:
            # 完成合并请求
            async with self.lock:
                state = self.streams.get(stream_id)
            if not state:
                return await self.send_error(
                    websocket, f"流不存在: {stream_id}", echo=echo
                )

            try:
                # 检查是否所有分片都已接收
                if not state.is_complete():
                    return await self.send_error(
                        websocket,
                        f"分片未收齐，已收 {len(state.received_chunks)}/{state.total_chunks}",
                        echo=echo,
                    )

                final_path = state.assemble_file()
                # 从活跃流中移除
                async with self.lock:
                    del self.streams[stream_id]

                # 返回成功响应
                response = {
                    "status": "ok",
                    "retcode": 0,
                    "data": {
                        "status": "file_complete",
                        "file_path": str(final_path.absolute()),
                        "file_size": state.file_size,
                        "sha256": state.expected_sha256,
                    },
                    "echo": echo,
                }
                await websocket.send(json.dumps(response))
            except Exception as e:
                await self.send_error(websocket, f"文件合并失败: {e}", echo=echo)
                # 清理失败的流
                async with self.lock:
                    if stream_id in self.streams:
                        state.cleanup()
                        del self.streams[stream_id]
            return

        # 分片上传请求
        chunk_data_b64 = params.get("chunk_data")
        chunk_index = params.get("chunk_index")
        total_chunks = params.get("total_chunks")
        file_size = params.get("file_size")
        expected_sha256 = params.get("expected_sha256")
        filename = params.get("filename")
        file_retention = params.get("file_retention", 0)

        # 参数校验
        if any(
                v is None
                for v in [
                    chunk_data_b64,
                    chunk_index,
                    total_chunks,
                    file_size,
                    expected_sha256,
                    filename,
                ]
        ):
            return await self.send_error(websocket, "缺少必要参数", echo=echo)

        try:
            chunk_index = int(chunk_index)
            total_chunks = int(total_chunks)
            file_size = int(file_size)
        except ValueError:
            return await self.send_error(websocket, "参数类型错误", echo=echo)

        # 解码分片数据
        try:
            chunk_data = base64.b64decode(chunk_data_b64)
        except Exception:
            return await self.send_error(
                websocket, "分片数据 base64 解码失败", echo=echo
            )

        # 获取或创建流状态
        async with self.lock:
            state = self.streams.get(stream_id)
            if not state:
                # 首次分片，创建新流
                state = StreamState(
                    stream_id=stream_id,
                    total_chunks=total_chunks,
                    file_size=file_size,
                    expected_sha256=expected_sha256,
                    filename=filename,
                    file_retention=file_retention,
                )
                self.streams[stream_id] = state

        # 检查参数一致性（可选）
        if (
                state.total_chunks != total_chunks
                or state.file_size != file_size
                or state.expected_sha256 != expected_sha256.lower()
        ):
            return await self.send_error(websocket, "流参数与已存在的不一致", echo=echo)

        # 保存分片
        try:
            is_new = state.add_chunk(chunk_index, chunk_data)
        except Exception as e:
            return await self.send_error(websocket, f"保存分片失败: {e}", echo=echo)

        # 构建响应
        response = {
            "status": "ok",
            "retcode": 0,
            "data": {
                "received_chunks": len(state.received_chunks),
                "total_chunks": state.total_chunks,
            },
            "echo": echo,
        }
        await websocket.send(json.dumps(response))

    async def send_error(self, websocket, message: str, echo: str = None):
        """发送错误响应"""
        response = {
            "status": "failed",
            "retcode": 100,  # 自定义错误码
            "data": None,
            "message": message,
            "echo": echo,
        }
        await websocket.send(json.dumps(response))

    async def run(self):
        """启动服务器"""
        # 启动清理任务
        self.cleanup_task = asyncio.create_task(self.start_cleanup())

        async with websockets.serve(self.handle_connection, HOST, PORT):
            print(f"WebSocket 服务器启动在 ws://{HOST}:{PORT}")
            if self.token:
                print(f"认证已启用，Token: {self.token}")
            else:
                print("认证未启用（Token 为空）")
            print(f"上传文件保存目录: {UPLOAD_DIR.absolute()}")
            print(f"临时文件目录: {TEMP_DIR.absolute()}")
            await asyncio.Future()  # 运行 forever


if __name__ == "__main__":
    # 可以从环境变量读取 Token，覆盖默认值
    token = os.environ.get("NAPCAT_TOKEN", TOKEN)
    server = UploadServer(token=token)
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n服务器关闭")

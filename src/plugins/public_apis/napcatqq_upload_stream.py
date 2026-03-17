#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NapCat OneBot WebSocket 文件流上传测试脚本
用于测试 UploadFileStream 接口的一次性分片上传功能
"""

import argparse
import asyncio
import base64
import hashlib
import json
import uuid
from pathlib import Path
from typing import List, Optional

import websockets

from . import config


class OneBotUploadTester:
    def __init__(self, ws_url: str = config.upload_ws_url, access_token: Optional[str] = config.upload_ws_token):
        self.ws_url = ws_url
        self.access_token = access_token
        self.websocket = None

    async def connect(self):
        """连接到 OneBot WebSocket"""
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        # print(f"连接到 {self.ws_url}")
        self.websocket = await websockets.connect(self.ws_url, additional_headers=headers)
        # print("WebSocket 连接成功")

    async def disconnect(self):
        """断开 WebSocket 连接"""
        if self.websocket:
            await self.websocket.close()
            # print("WebSocket 连接已断开")

    def calculate_file_chunks(self, file_path: str, chunk_size: int = 64) -> tuple[List[bytes], str, int]:
        """
        计算文件分片和 SHA256
        
        Args:
            file_path: 文件路径
            chunk_size: 分片大小（默认64字节）
            
        Returns:
            (chunks, sha256_hash, total_size)
        """
        chunks = []
        hasher = hashlib.sha256()
        total_size = 0

        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
                hasher.update(chunk)
                total_size += len(chunk)

        sha256_hash = hasher.hexdigest()
        # print(f"文件分析完成:")
        # print(f"  - 文件大小: {total_size} 字节")
        # print(f"  - 分片数量: {len(chunks)}")
        # print(f"  - SHA256: {sha256_hash}")

        return chunks, sha256_hash, total_size

    async def send_action(self, action: str, params: dict, echo: str = None) -> dict:
        """发送 OneBot 动作请求"""
        if not echo:
            echo = str(uuid.uuid4())

        message = {
            "action": action,
            "params": params,
            "echo": echo
        }

        # print(f"发送请求: {action}")
        await self.websocket.send(json.dumps(message))

        # 等待响应
        while True:
            response = await self.websocket.recv()
            data = json.loads(response)

            # 检查是否是我们的响应
            if data.get("echo") == echo:
                return data
            else:
                # 可能是其他消息，继续等待
                # print(f"收到其他消息: {data}")
                continue

    async def upload_file_stream_batch(self, file_path: str, chunk_size: int = 64, file_retention: int = 120) -> str:
        """
        一次性批量上传文件流
        
        Args:
            file_path: 要上传的文件路径
            chunk_size: 分片大小, 单位 byte
            file_retention: 文件保存时间, 单位 s
            
        Returns:
            上传完成后的文件路径
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 分析文件
        chunks, sha256_hash, total_size = self.calculate_file_chunks(str(file_path), chunk_size)
        stream_id = str(uuid.uuid4())

        # print(f"\n开始上传文件: {file_path.name}")
        # print(f"流ID: {stream_id}")

        # 一次性发送所有分片
        total_chunks = len(chunks)

        for chunk_index, chunk_data in enumerate(chunks):
            # 将分片数据编码为 base64
            chunk_base64 = base64.b64encode(chunk_data).decode('utf-8')

            # 构建参数
            params = {
                "stream_id": stream_id,
                "chunk_data": chunk_base64,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "file_size": total_size,
                "expected_sha256": sha256_hash,
                "filename": file_path.name,
                "file_retention": file_retention * 1000
            }

            # 发送分片
            response = await self.send_action("upload_file_stream", params)

            if response.get("status") != "ok":
                raise Exception(f"上传分片 {chunk_index} 失败: {response}")

            # 解析流响应
            # stream_data = response.get("data", {})
            # print(f"分片 {chunk_index + 1}/{total_chunks} 上传成功 "
            #       f"(接收: {stream_data.get('received_chunks', 0)}/{stream_data.get('total_chunks', 0)})")

        # 发送完成信号
        # print(f"\n所有分片发送完成，请求文件合并...")
        complete_params = {
            "stream_id": stream_id,
            "is_complete": True
        }

        response = await self.send_action("upload_file_stream", complete_params)

        if response.get("status") != "ok":
            raise Exception(f"文件合并失败: {response}")

        result = response.get("data", {})

        if result.get("status") == "file_complete":
            # print(f"✅ 文件上传成功!")
            # print(f"  - 文件路径: {result.get('file_path')}")
            # print(f"  - 文件大小: {result.get('file_size')} 字节")
            # print(f"  - SHA256: {result.get('sha256')}")
            return result.get('file_path')
        else:
            raise Exception(f"文件状态异常: {result}")

    async def test_upload(self, file_path: str, chunk_size: int = 64):
        """测试文件上传"""
        try:
            await self.connect()

            # 执行上传
            uploaded_path = await self.upload_file_stream_batch(file_path, chunk_size)

            print(f"\n🎉 测试完成! 上传后的文件路径: {uploaded_path}")

        except Exception as e:
            print(f"❌ 测试失败: {e}")
            raise
        finally:
            await self.disconnect()


def create_test_file(file_path: str, size_mb: float = 1):
    """创建测试文件"""
    size_bytes = int(size_mb * 1024 * 1024)

    with open(file_path, 'wb') as f:
        # 写入一些有意义的测试数据
        test_data = b"NapCat Upload Test Data - " * 100
        written = 0
        while written < size_bytes:
            write_size = min(len(test_data), size_bytes - written)
            f.write(test_data[:write_size])
            written += write_size

    print(f"创建测试文件: {file_path} ({size_mb}MB)")


async def main():
    parser = argparse.ArgumentParser(description="NapCat OneBot 文件流上传测试")
    parser.add_argument("--url", default="ws://localhost:3001", help="WebSocket URL")
    parser.add_argument("--token", help="访问令牌")
    parser.add_argument("--file", help="要上传的文件路径")
    parser.add_argument("--chunk-size", type=int, default=64 * 1024, help="分片大小(字节)")
    parser.add_argument("--create-test", type=float, help="创建测试文件(MB)")

    args = parser.parse_args()

    # 创建测试文件
    if args.create_test:
        test_file = "test_upload_file.bin"
        create_test_file(test_file, args.create_test)
        if not args.file:
            args.file = test_file

    if not args.file:
        print("请指定要上传的文件路径，或使用 --create-test 创建测试文件")
        return

    # 创建测试器并运行
    tester = OneBotUploadTester(args.url, args.token)
    await tester.test_upload(args.file, args.chunk_size)


if __name__ == "__main__":
    asyncio.run(main())

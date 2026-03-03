#!/bin/bash
set -e

echo "🔄 等待数据库就绪..."

# 等待 MySQL 可用（使用 text() 包装 SQL）
until python -c "
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

db_url = os.getenv('SQLALCHEMY_DATABASE_URL', '')
if not db_url:
    print('❌ SQLALCHEMY_DATABASE_URL not set')
    exit(1)

async def test():
    engine = None
    try:
        engine = create_async_engine(db_url)
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
            print('✅ Database connected')
        return True
    except Exception as e:
        print(f'❌ Database not ready: {e}')
        return False
    finally:
        if engine:
            await engine.dispose()

result = asyncio.run(test())
exit(0 if result else 1)
"; do
    echo "⏳ 重试中... "
    sleep 3
done

echo "🚀 执行数据库迁移..."
nb orm upgrade

echo "✅ 迁移完成，启动机器人..."
exec "$@"
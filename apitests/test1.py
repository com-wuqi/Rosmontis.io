import asyncio
from openai import AsyncOpenAI

async def test():
    client = AsyncOpenAI(api_key="sk-4729afe5345d41c08fd6805e4f478bb1", base_url="https://api.deepseek.com")
    try:
        models = await client.models.list()
        print([m.id for m in models.data])
    except Exception as e:
        print("失败:", e)

asyncio.run(test())
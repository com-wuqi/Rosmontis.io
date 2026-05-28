import asyncio

from nonebot import require

require("src.plugins.public_apis")
import src.plugins.public_apis as public_apis

semaphore_download = asyncio.Semaphore(20)

TokenBucket = public_apis.TokenBucket
download_file = public_apis.download_file
upload_file = public_apis.upload_file

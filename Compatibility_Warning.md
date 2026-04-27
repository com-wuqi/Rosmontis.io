# 兼容性问题

这里汇总了所有使用 非 onebot 接口的接口, 存在过时风险

## get_private_file_url

### 调用

参数: `file_id`: 文件唯一ID, 可以通过 `nonebot.adapters.onebot.v11.MessageEvent` 获取

期望的返回值: { "url": 文件可供下载的url, 字符串 }

### 受到影响的内容

`src/plugins/self_build_tts/message_handle.py`

1. function : qwen3_clone_got_ref_aud bot.call_api调用
2. function : qwen3_gen_got_file_obj bot.call_api调用

### 引入的依据

[napcat doc](https://napneko.github.io/onebot/api#%E6%96%87%E4%BB%B6%E7%9B%B8%E5%85%B3)

### 可能的缓解方案

目前没有实现, 保留想法

````python
from nonebot import on_message, logger
from nonebot.adapters.onebot.v11 import MessageEvent

_debug_message = on_message(priority=1, block=False)


@_debug_message.handle()
async def debug_message_handle(event: MessageEvent):
    # logger.debug("MessageEvent.message_type: {}".format(event.message_type))
    logger.debug("MessageEvent.message: {}".format(event.message))
    return
````

这里的返回值是类似：

`[file:file=xxx.xxx,file_id=xxxxx,file_size=251017]`

`[CQ:image,summary=,file=xxxx.jpg,sub_type=0,url=http[s]://multimedia.nt.qq.com.cn/download?appid=xxx&amp;fileid=xxx&amp;rkey=xxx,file_size=251017]`

或许可以考虑通过处理 `CQ` code 来获取文件，笔者简单测试发现报错如下（大概率是拼接错误）

````json
{
  "retcode": -5503010,
  "retmsg": "invalid rkey",
  "retryflag": 1
}
````

前文接口不可用时候考虑重试这类方案

## get_cookies | get_clientkey

## 调用

参数: json 参考 `src/plugins/Qzone_toolkit/napcat_websockets_api.py`

期望的返回值: dict 参考 `src/plugins/Qzone_toolkit/napcat_websockets_api.py`

### 受到影响的内容

`src/plugins/Qzone_toolkit/napcat_websockets_api.py` 整个文件

插件 `src/plugins/Qzone_toolkit` 整个插件

插件 `src/plugins/qzone_handle` 作为下游, 依赖于这个插件

### 引入的依据

[napcat doc](https://napneko.github.io/onebot/api#%E8%B4%A6%E5%8F%B7%E7%9B%B8%E5%85%B3)

[napcat doc](https://napneko.github.io/onebot/api#%E5%85%B6%E4%BB%96%E5%8A%9F%E8%83%BD)


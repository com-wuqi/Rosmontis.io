# 兼容性问题

这里汇总了所有使用 非 onebot 接口的接口, 存在过时风险

## get_private_file_url

### 调用

参数: `file_id`: 文件唯一ID, 可以通过 `nonebot.adapters.onebot.v11.MessageEvent` 获取

期望的返回值: { "url": 文件可供下载的url, 字符串 }

### 受到影响的内容

`src/plugins/self_build_tts/message_handle.py`

1. ~~函数 `qwen3_clone_got_ref_aud` 通过 `bot.call_api` 调用~~ → 已迁移至 `download_attachment()`
2. ~~函数 `qwen3_gen_got_file_obj` 通过 `bot.call_api` 调用~~ → 已迁移至 `download_attachment()`

`src/plugins/ai_file_reader/__init__.py`

1. ~~函数 `ai_file_reader` 通过 `bot.call_api` 调用~~ → 已迁移至 `download_to_cache()`

### 引入的依据

[napcat doc](https://napneko.github.io/onebot/api#%E6%96%87%E4%BB%B6%E7%9B%B8%E5%85%B3)


---

## get_cookies | get_clientkey

参数: json 参考 `src/plugins/Qzone_toolkit/napcat_websockets_api.py`

期望的返回值: dict 参考 `src/plugins/Qzone_toolkit/napcat_websockets_api.py`

### 受到影响的内容

`src/plugins/Qzone_toolkit/napcat_websockets_api.py` 整个文件

插件 `src/plugins/Qzone_toolkit` 整个插件

插件 `src/plugins/qzone_handle` 作为下游, 依赖于这个插件

### 引入的依据

[napcat doc](https://napneko.github.io/onebot/api#%E8%B4%A6%E5%8F%B7%E7%9B%B8%E5%85%B3)

[napcat doc](https://napneko.github.io/onebot/api#%E5%85%B6%E4%BB%96%E5%8A%9F%E8%83%BD)


---

## `src/plugins/self_build_tts` — 缺少维护和测试

> 状态：部分迁移至跨平台，未经过飞书端到端测试。

### 硬编码接口

| 问题 | 位置 | 说明 |
|------|------|------|
| Gradio API 路径硬编码 | `tts_api_handle.py:128-191` | `/run_instruct`, `/run_voice_design`, `/save_prompt`, `/load_prompt_and_gen` 依赖服务端实现 |
| GPT-SoVITS URL 手动拼接 | `tts_api_handle.py:35-58` | 参数名依赖 WebUI 版本，升级即断裂 |
| 上传-下载双重跳 | 全局 | 文件先上传到第三方托管 → 飞书再下载，多一跳 |
| `upload_file` 语义错误 | `build_file_message` 飞书路径 | 传 HTTP URL 作为 `file_key` |

### 死代码

`get_private_file_from_url` (`tts_api_handle.py:195`) — 签名 `user_id: int` 与 VARCHAR 迁移不一致，无调用方。


---

## feishu 适配器 — 已知不稳定点

### `get_adapter_name` 字符串匹配

基于 `bot.type` 字符串匹配（`"OneBot" in name` → onebot, `"Feishu" in name or "飞书" in name` → feishu）。若 NoneBot 上游改名或新增 adapter，匹配即失效。

### 适配层过度暴露的 API

`is_onebot_event`、`is_feishu_event`、`is_onebot`、`is_feishu` 被外部调用 0 次，全是适配层内部辅助函数。建议改 `_` 前缀私有化。

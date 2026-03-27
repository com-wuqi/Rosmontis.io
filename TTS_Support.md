# 自建TTS支持

考虑到不同模型对语言的支持不同, 我们仅封装了 `tts`+`文本` 形式的接口, 对不同模型的支持不同

本文的内容可能已经过时, 上次维护 `2026.3`

需要维护, 请提交 `issue`

## 集成的命令

### GPT-SoVITS

[命令前缀]gpt-tts [待合成文本] -- 运行已有的模型进行推理, 返回生成的文件

### Qwen3-TTS

[命令前缀]qwen3-cvoice [待合成文本] -- 运行已有的模型进行推理, 返回生成的文件

[命令前缀]qwen3-vdesign [待合成文本] -- 运行已有的模型进行推理, 返回生成的文件

[命令前缀]qwen3_clone -- 根据向导, 提供音频文件和对应的文本, 返回模型文件

[命令前缀]qwen3_gen -- 根据向导, 提供模型文件和带生成的文本, 返回音频文件

## 支持的项目

### GPT-SoVITS

我们使用时最新的提交 : [2d9193b](https://github.com/RVC-Boss/GPT-SoVITS/commit/2d9193b0d3c0eae0c3a14d8c68a839f1bae157dc)

[GPT-SoVITS yuque](https://www.yuque.com/baicaigongchang1145haoyuangong/ib3g1e)

yuque 文档里面包含了如何使用第三方的模型, 目前, 对话交互仍然不支持训练, 请使用 `webui`

> 将GPT模型（ckpt后缀）放入GPT_weights_v4文件夹，SoVITS模型（pth后缀）放入SoVITS_weights_v4文件夹

[GPT-SoVITS GitHub](https://github.com/RVC-Boss/GPT-SoVITS)

我们使用 [api_v2.py](https://github.com/RVC-Boss/GPT-SoVITS/blob/main/api_v2.py) 构建了对 TTS 功能的支持.

`语言`和`模型` 的切换需要修改配置文件,
手动配置涵盖 `tts接口地址` `参考音频地址` `参考音频的文本内容` `参考音频同种的语言` 和 `请求文本的语言` ,
详见 [.env.prod](.env.prod)

如果需要修改启动时加载的模型, 在 `GPT-SoVITS` 根目录之下的 `GPT_SoVITS/configs/tts_infer.yaml` 的 `custom:` 内:

`t2s_weights_path` 是 `.ckpt` , `vits_weights_path` 是 `.pth` 文件

在调用中, 我们填充了大量默认参数, 参考 [tts_api_handle.py](src/plugins/self_build_tts/tts_api_handle.py)
的 ` built_gpt_sovits_url_tts` 方法, 您仍然可以自定义相关参数, 也欢迎通过 `PR` 帮助我们提供更好的TTS支持

启动 `api_v2.py` 的命令和参数见其本身

Tip: 切换模型时, 请使用基于 `GPT-SoVITS` 根目录的 `相对目录` ,
例如 : `GPT_weights_v4/纯烬艾雅法拉-e10.ckpt` 和 `SoVITS_weights_v4/纯烬艾雅法拉_e10_s180_l32.pth` , 对应关系请参考上文

### Qwen3-TTS

我们使用时最新的提交 : [022e286](https://github.com/QwenLM/Qwen3-TTS/commit/022e286b98fbec7e1e916cb940cdf532cd9f488e)

[QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS/)

我们使用的是官方提供的模型文件, 如何部署 `Qwen3-TTS` 参考它的
github [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS/)

注意, `Qwen3-TTS` 的部署方案没有安装支持 `cuda` 的 `pytorch` , 你需要根据自己的版本进行替换,
笔者测试时使用的是 CUDA 12.8 + PyTorch 2.9.0 的方案

启动时, 我们使用的是 `qwen-tts-demo [下载的模型文件夹]` 方式启动, 其他方式详见 Qwen3-TTS 
# 自建TTS支持

考虑到不同模型对语言的支持不同, 我们仅封装了 `tts`+`文本` 形式的接口,

本文的内容可能已经过时, 上次维护 `2026.3`

需要维护, 请提交 `issue`

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

Tip: 切换模型时, 请使用基于 `GPT-SoVITS` 根目录的 `相对目录` ,
例如 : `GPT_weights_v4/纯烬艾雅法拉-e10.ckpt` 和 `SoVITS_weights_v4/纯烬艾雅法拉_e10_s180_l32.pth` , 对应关系请参考上文


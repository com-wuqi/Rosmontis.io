# Rosmontis.io

基于 nonebotv2 + onebotv11 的 跨平台的 开源机器人实现

## 已经实现

待施工

## 快速开始

### 准备环境

上游实现: 本项目依赖 onebotv11 , 理论上任何支持 onebotv11 的信息提供方都可以接入

ai相关: openai标准库实现, 暂时不支持图片和文件上传

建议使用 `conda` 并为项目配置专用的虚拟环境, 注意需要 `python3>=3.12`, 我们测试时使用的是 3.14.2

### 安装项目依赖

```bash
pip install -r requirements.txt
```

使用 `nb plugin` 更新所需插件

必要时参考 https://nonebot.dev/docs/quick-start 安装 `pipx` 和 `nonebot` 本体

依赖安装问题请开 `discussion`

### 准备数据库

推荐使用 mysql + aiomysql , 不支持 sqlite

安装数据库不再赘述, 记得创建空数据库用于初始化即可

```bash
nb orm upgrade # 一般用不上, 数据库更新之后需要
```

### 调整配置文件

这个项目通过 `.env.prod` 来配置

详见文件 [.env.prod](.env.prod) , 酌情修改

### 然后?

然后就能用了, 还有问题可提 issue

## 依赖导出方式:

```bash
pip list --format=freeze > requirements.txt
```

## 许可证

本项目采用 [MIT 许可证](LICENSE) 进行许可。
除了主要作者外，本项目还受益于众多贡献者的努力，详见 [CONTRIBUTORS](CONTRIBUTORS) 文件。
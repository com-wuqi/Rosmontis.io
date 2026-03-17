# Rosmontis.io

基于 nonebotv2 + onebotv11 的 跨平台的 开源机器人实现

## 已经实现

文档 [__init__.py](src/plugins/easyhelper/__init__.py)

## 迁移

从旧版本迁移:

由于我们更新的提示词的添加, 您可能不得不执行 `ai remove` 并按照提示完成删除数据库内对话才能正常使用

## 手动部署 (推荐)

### 准备环境

上游实现: 本项目依赖 onebotv11 , 理论上任何支持 onebotv11 的信息提供方都可以接入

ai相关: openai标准库实现, 支持自定义 MCP 服务 (支持sse, stdio, streamable-http)

建议使用 `conda` 并为项目配置专用的虚拟环境, 注意需要 `python3>=3.12`, 我们测试时使用的是 3.14.2

MCP 调用需要 `nodejs` `npm` `npx`, 建议安装,

复制文件 [src/plugins/mcp_support/example.mcp_config.py](src/plugins/mcp_support/example.mcp_config.py) 为
`src/plugins/mcp_support/mcp_config.py`

如果不使用, 进入文件 [mcp_config.py](src/plugins/mcp_support/mcp_config.py) 删除依赖 `nodejs` 的服务器

### 安装项目依赖

准备虚拟环境, 激活虚拟环境不再赘述,

```bash
pip install -r requirements.txt
```

使用 `nb plugin` 更新所需插件

必要时参考 https://nonebot.dev/docs/quick-start 安装 `pipx` 和 `nonebot` 本体

依赖安装问题请开 `discussion`

### 准备数据库

推荐使用 mysql + aiomysql ,

根据配置文件中的数据库名称(mysql需要)(默认为data), 需要登录后创建空数据库

```sql
CREATE
DATABASE data
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

支持 sqlite , 需要修改 `pymysql`为 `aiosqlite`, 例如, 注意修改其他配置项

```dotenv
SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:///data.db
APSCHEDULER_CONFIG={"apscheduler.jobstores":{"default":{"type":"sqlalchemy","url":"sqlite:///data.db","tablename":"apscheduler_jobs"}}}
```

安装数据库不再赘述, 记得创建空数据库用于初始化即可

```bash
nb orm upgrade # 第一次使用需要执行, 数据库更新之后也需要
```

### 调整配置文件

适当修改 [.env.prod](.env.prod) ,[mcp_config.py](src/plugins/mcp_support/mcp_config.py)

### 然后?

然后就能用了, 还有问题可提 issue

## docker 手动构建

克隆仓库, 进入目录,

复制文件 [src/plugins/mcp_support/example.mcp_config.py](src/plugins/mcp_support/example.mcp_config.py) 为
`src/plugins/mcp_support/mcp_config.py`

请删除 [mcp_config.py](src/plugins/mcp_support/mcp_config.py) 依赖 `nodejs` 的服务器

注意, 容器部署**一般**没办法通过 `stdio` 建立连接, 所以需要修改 [docker-compose.yml](docker-compose.yml) 在容器内部署 或者
修改网络来访问其他服务器

```bash
sudo docker-compose --env-file .env.prod up -d
```

适当修改 [.env.prod](.env.prod) ,[mcp_config.py](src/plugins/mcp_support/mcp_config.py)

```bash
sudo docker logs -f napcat
```
手动登录, 然后进入webui(token在上面)(一般是 http://127.0.0.1:6099), 添加 网络配置

类型是ws服务器, 名称随意,

Host: 0.0.0.0 ,

Port: 3001 ,

选择启用 ,

token: 和 .env.prod 的 ONEBOT_ACCESS_TOKEN和NAPCATAPI__UPLOAD_WS_TOKEN 相同

```bash
sudo docker logs -f rosbot # 检查是否连接成功
```

## docker 使用构建产物

windows用户请考虑不用docker部署或者手动打包, 构建产物不含 windows 支持

注意, 构建产物不一定包含最新的功能(仅构建release分支), 可以 `fork` 然后手动触发 `action` 构建

自己 `fork` 请修改 `.env.prod` 的 `#IMAGE=` , 取消注释并改为你的构建产物地址

打开文件 [docker-compose.yml](docker-compose.yml) , 找到

```yml
services:
  # 机器人服务
  rosbot:
    build:
      context: .
      dockerfile: Dockerfile
    # image: ${IMAGE:-ghcr.io/com-wuqi/rosmontis.io:latest}
    container_name: rosbot
    restart: unless-stopped
```

修改为:

```yml
services:
  # 机器人服务
  rosbot:
    # build:
    #   context: .
    #   dockerfile: Dockerfile
    image: ${IMAGE:-ghcr.io/com-wuqi/rosmontis.io:latest}
    container_name: rosbot
    restart: unless-stopped
```

注意前往: https://github.com/com-wuqi/Rosmontis.io/pkgs/container/rosmontis.io 检查标签,
将 `latest` 换为最新的构建

然后进行上文的 `docker 手动构建` 过程 .

## 依赖导出方式:

```bash
pip-chill > requirements.txt
```

## 引用的其他项目

https://github.com/NapNeko/NapCatQQ

https://github.com/gfhdhytghd/qzone-toolkit

https://github.com/sansenjian/quick-e2b-sandbox

## 小工具

[compare_env.py](compare_env.py) : 比较配置文件的环境变量条目是否相同

## 许可证

本项目采用 [MIT 许可证](LICENSE) 进行许可。
除了主要作者外，本项目还受益于众多贡献者的努力，详见 [CONTRIBUTORS](CONTRIBUTORS) 文件。

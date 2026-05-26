# Rosmontis - 现代化AI机器人

![License](https://img.shields.io/github/license/com-wuqi/Rosmontis.io)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![NoneBot](https://img.shields.io/badge/NoneBot-v2.x-green)
![OneBot](https://img.shields.io/badge/OneBot-v11-yellow)

**Rosmontis**（迷迭香）是一个基于 **NoneBot v2** 框架和 **OneBot v11** 协议的现代化、可扩展的开源机器人实现。项目名源于《明日方舟》中的干员。

## ✨ 核心特性

### 🚀 现代化技术栈

- **Python 3.12+**: 最新的异步编程特性
- **NoneBot 2.5+**: 高性能异步机器人框架
- **SQLAlchemy 2.0 + Alembic**: 强大的ORM和数据库迁移
- **MCP (Model Context Protocol)**: 先进的工具调用协议

### 🤖 AI原生集成

- **多模型支持**: OpenAI API标准兼容，支持自定义AI提供商
- **MCP工具链**: 支持SSE、stdio、streamable-http三种通信方案
- **文件智能处理**: 图像OCR、文档解析、多媒体处理
- **代码沙箱**: E2B集成，安全执行用户代码
- **知识库检索**: ChromaDB向量数据库支持

### 🎨 多媒体处理

- **音乐服务**: 妖狐数据API集成，支持多平台音源
- **图像处理**: Pillow集成，支持图片识别与处理
- **TTS语音合成**: GPT-SoVITS、Qwen3-TTS支持
- **文件上传**: 跨平台文件传输服务

### 🔧 企业级特性

- **Sentry监控**: 生产环境错误追踪
- **APScheduler**: 分布式任务调度
- **数据库支持**: MySQL + SQLite双引擎
- **Docker部署**: 完整的容器化方案
- **GitHub Actions**: 自动化CI/CD流水线

## 📁 项目结构

```
Rosmontis/
├── src/plugins/              # 核心插件目录
│   ├── aihelper/            # AI助手核心，对话管理
│   ├── mcp_support/         # MCP协议支持，工具调用
│   ├── ai_file_reader/      # 文件智能读取（OCR等）
│   ├── yaohud/              # 妖狐数据API，多媒体处理
│   ├── public_apis/         # 公开API服务，文件上传
│   ├── self_build_tts/      # 自建TTS服务（实验性）
│   ├── qzone_handle/        # QQ空间接口处理
│   ├── hitokoto/            # 一言服务
│   ├── easyhelper/          # 简易助手功能
│   └── hooked_mcp_tools/    # MCP工具钩子
├── migrations/              # 数据库迁移文件
├── server/                  # 辅助服务器文件
├── mcp_workdir/            # MCP工作目录
├── cache/                   # 缓存目录
├── data/                    # 数据目录
├── .github/workflows/       # CI/CD配置
├── docker-compose.yml       # Docker编排配置
├── Dockerfile               # Docker镜像构建
├── bot.py                   # 机器人入口文件
├── pyproject.toml           # 项目配置
├── requirements.txt         # Python依赖
├── .env.prod                # 生产环境配置
└── README.md                # 项目说明
```

## 🚀 快速开始

另附旧版教程，更详细但是更复杂 [extra_README.md](extra_README.md)

### 方式一：手动部署 (推荐)

1. **环境要求**
   - Python 3.12+
   - Node.js 18+ (用于MCP支持)
   - MySQL 8.0+ 或 SQLite
   - Napcat 实例 (请参考`https://napneko.github.io/`)

2. **创建虚拟环境**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # 或 venv\Scripts\activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **数据库初始化**
   ```bash
   # MySQL示例
   CREATE DATABASE data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
   ```bash
   vim .env.prod
   # 编辑 .env.prod 文件，配置数据库连接, Napcat连接等
   ```

   ```bash
   # 应用数据库迁移
   nb orm upgrade
   ```

5. **配置MCP**
   ```bash
   cp src/plugins/mcp_support/example_mcp_config.py src/plugins/mcp_support/mcp_config.py
   # 编辑 mcp_config.py 配置MCP服务器
   ```

6. **启动机器人**
   ```bash
   nb run
   ```

### 方式二：Docker部署 (缺少测试)

1. **克隆项目**
   ```bash
   git clone https://github.com/com-wuqi/Rosmontis.io.git
   cd Rosmontis.io
   ```

2. **配置环境变量**
   ```bash
   vim .env.prod
   # 编辑 .env.prod 文件，配置数据库连接等
   ```

3. **启动服务**
   ```bash
   docker-compose --env-file .env.prod up -d
   ```

4. **配置NapCatQQ**
   - 访问 `http://127.0.0.1:6099` (NapCat管理界面)
   - 添加WebSocket服务器配置：
      - Host: 0.0.0.0
      - Port: 3001
      - Token: 与 `.env.prod` 中的 `ONEBOT_ACCESS_TOKEN` 一致

## 🔧 功能配置

### AI配置

添加AI供应商：

```bash
# 在聊天窗口中执行
/ai cf add
# 按照向导配置AI API密钥和模型
```

支持的AI供应商：

- OpenAI系列（GPT-4, GPT-3.5）
- 通义千问
- 智谱AI
- 自定义供应商

### 插件配置

编辑 `.env.prod` 文件配置插件：

(这里仅仅截取一部分～)

```env
# AI助手总开关
AIHELPER__IS_ENABLE=true

# 文件读取能力
AI_FILE_READER__IS_ENABLE=true

# 妖狐数据API
YAOHUD__IS_ENABLE=true
YAOHUD__API_KEY=your_key
YAOHUD__API_SECRET=your_secret

# MCP支持
MCPSUPPORT__IS_ENABLE=true

# 文件上传服务
PUBLICAPI__IS_ENABLE_UPLOAD=true
```

### 插件管理

```bash
# 查看已安装插件
nb plugin list

# 安装新插件
nb plugin install <plugin-name>

# 卸载插件
nb plugin uninstall <plugin-name>
```

## 📚 详细文档

### 数据库管理

```bash
# 创建新迁移
nb orm revision --autogenerate -m "描述"

# 应用迁移
nb orm upgrade

# 回滚迁移
nb orm downgrade -1

# 查看迁移历史
nb orm history
```

### 任务调度

通过APScheduler支持定时任务：

```python
from nonebot_plugin_apscheduler import scheduler
from nonebot.adapters.onebot.v11 import Bot


@scheduler.scheduled_job("cron", hour=8)
async def daily_reminder(bot: Bot):
   await bot.send_group_msg(group_id=123456, message="早安！")
```

### 错误监控

集成Sentry进行错误追踪：

1. 注册 [Sentry](https://sentry.io/) 账户
2. 创建Python项目
3. 在 `.env.prod` 中配置 `SENTRY_DSN`

## 🛠️ 开发指南

### 创建新插件

```bash
nb plugin create
```

然后按照指导完成即可

### 代码规范

```bash
# 代码格式化
ruff format .

# 代码检查
ruff check .

# 类型检查
pyright .
```

### 测试（施工中）

```bash
# 运行单元测试
pytest tests/

# 覆盖率测试
pytest --cov=src tests/
```

## 🔍 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查MySQL服务状态
   - 确认数据库用户权限
   - 验证连接字符串格式

2. **NapCat连接失败**
   - 检查WebSocket服务器配置
   - 确认端口3001未被占用
   - 验证Token一致性

3. **AI API调用失败**
   - 检查API密钥有效性
   - 确认网络代理配置
   - 验证模型名称正确性

4. **插件加载失败**
   - 检查插件依赖安装
   - 确认配置文件格式
   - 查看日志文件错误信息

### 日志查看

```bash
# Docker部署
docker logs -f rosbot

# 手动部署
tail -f logs/bot.log

# 详细调试
LOG_LEVEL=DEBUG python bot.py
```

## 🤝 贡献指南

### 开发流程

1. **Fork项目**
2. **创建功能分支**
   ```bash
   git checkout -b feat/new-feature
   ```
3. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   ```
4. **推送到远程**
   ```bash
   git push origin feat/new-feature
   ```
5. **创建Pull Request**

### 提交规范

- `feat`: 新功能
- `fix`: bug修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 进行许可。

除了主要作者外，本项目还受益于众多贡献者的努力，详见 [CONTRIBUTORS](CONTRIBUTORS) 文件。

## 🔗 相关项目

- [NapCatQQ](https://github.com/NapNeko/NapCatQQ) - QQ协议实现
- [qzone-toolkit](https://github.com/gfhdhytghd/qzone-toolkit) - QQ空间工具
- [quick-e2b-sandbox](https://github.com/sansenjian/quick-e2b-sandbox) - 代码沙箱

## 📞 支持与联系

- **Issues**: [GitHub Issues](https://github.com/com-wuqi/Rosmontis.io/issues)
- **Discussions**: [GitHub Discussions](https://github.com/com-wuqi/Rosmontis.io/discussions)
- **作者**: [@com-wuqi](https://github.com/com-wuqi)

---

**🔄 持续更新中...** 欢迎Star和Fork，一起构建更好的Rosmontis！

> *"让智能在指尖绽放。"*

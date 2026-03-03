# Rosmontis.io Dockerfile
FROM python:3.14-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt pyproject.toml ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir nb-cli

# 复制项目文件
COPY . .

# 创建非 root 用户运行（安全最佳实践）
RUN useradd -m -u 1000 rosbot && chown -R rosbot:rosbot /app
USER rosbot

# 暴露端口（根据 OneBot 适配器需要）
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import nonebot" || exit 1

# 复制入口脚本
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# 设置入口点
ENTRYPOINT ["docker-entrypoint.sh"]

# 启动命令
CMD ["python", "bot.py"]
# Rosmontis.io Dockerfile
FROM python:3.14-slim

# 使用官方 uv 镜像复制二进制文件
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/app/.venv

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装（利用 Docker 缓存层）
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# 复制入口脚本
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# 复制项目文件
COPY . .

# 创建非 root 用户运行（安全最佳实践）
RUN useradd -m -u 1000 rosbot && chown -R rosbot:rosbot /app
USER rosbot

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import nonebot" || exit 1

# 设置入口点
ENTRYPOINT ["docker-entrypoint.sh"]

# 启动命令
CMD ["python", "bot.py"]

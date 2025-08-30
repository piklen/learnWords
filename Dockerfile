# 多阶段构建Dockerfile
FROM python:3.11-slim AS base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 开发阶段
FROM base AS development

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads logs && chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 6773

# 开发环境命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6773", "--reload"]

# 生产阶段
FROM base AS production

# 复制应用代码
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p uploads logs && \
    chown -R appuser:appuser /app && \
    if [ -d "/app/scripts" ]; then find /app/scripts -name "*.sh" -type f -exec chmod +x {} \; || true; fi

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 6773

# 生产环境命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6773", "--workers", "4"]

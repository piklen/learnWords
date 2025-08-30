#!/bin/bash

# 智能教案生成平台启动脚本
# 端口号: 6783

echo "🚀 启动智能教案生成平台..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖包..."
pip install -r requirements.txt

# 检查Redis服务
echo "🔍 检查Redis服务..."
if ! command -v redis-cli &> /dev/null; then
    echo "⚠️  Redis未安装，某些功能可能无法正常工作"
else
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis服务运行正常"
    else
        echo "⚠️  Redis服务未启动，某些功能可能无法正常工作"
    fi
fi

# 检查PostgreSQL服务
echo "🔍 检查PostgreSQL服务..."
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL未安装，某些功能可能无法正常工作"
else
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        echo "✅ PostgreSQL服务运行正常"
    else
        echo "⚠️  PostgreSQL服务未启动，某些功能可能无法正常工作"
    fi
fi

# 创建必要的目录
echo "📁 创建必要目录..."
mkdir -p uploads
mkdir -p logs

# 初始化数据库
echo "🗄️  初始化数据库..."
python scripts/init_db.py

# 启动应用
echo "🌐 启动Web服务器 (端口: 6783)..."
echo "📊 API文档: http://localhost:6783/api/docs"
echo "🔗 健康检查: http://localhost:6783/health"
echo "🌐 前端界面: http://localhost:6783/"

# 使用uvicorn启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 6783 --reload

echo "🛑 服务器已停止"

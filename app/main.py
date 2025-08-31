from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from app.api.v1.api import api_router, websocket_router
from app.core.config_optimized import settings
from app.core.database_optimized import engine
from app.core.middleware import setup_middleware
from app.core.startup_optimized import setup_optimized_app, startup_manager, verify_system_health
from app.core.logging import setup_logging
from app.models import Base

# Setup logging
logger = setup_logging()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="智能教案生成平台 (优化版)",
    description="基于AI的智能教案生成系统 - 高性能优化版本",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 设置优化组件
app = setup_optimized_app(app)

# Setup middleware
setup_middleware(app)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Include WebSocket router (without prefix)
app.include_router(websocket_router)

# Mount static files
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("🚀 智能教案生成平台 (优化版) 启动中...")
    logger.info(f"🌐 服务器地址: {settings.server.host}:{settings.server.port}")
    logger.info(f"🔗 外部访问地址: http://localhost:{settings.server.port}")
    logger.info(f"📊 调试模式: {settings.server.debug}")
    logger.info(f"🔗 API前缀: {settings.server.api_prefix}")
    logger.info(f"📁 最大文件大小: {settings.storage.max_file_size / (1024*1024):.1f}MB")
    logger.info(f"🌐 WebSocket支持: 已启用")
    logger.info(f"📤 导出功能: 已启用")
    logger.info(f"💾 缓存系统: 已启用 (多层缓存)")
    logger.info(f"🔒 权限管理: 已启用")
    logger.info(f"⚡ API限流: 已启用 (智能限流)")
    logger.info(f"📊 监控系统: 已启用 (高级监控)")
    logger.info(f"🎯 任务调度: 已启用 (优先级队列)")
    logger.info(f"🤖 AI服务: {settings.ai.ai_provider} (容错机制)")
    
    # 显示系统健康状态
    try:
        health_status = await verify_system_health()
        logger.info(f"🏥 系统健康状态: {health_status['overall']}")
        if health_status['issues']:
            logger.warning(f"⚠️ 检测到问题: {', '.join(health_status['issues'])}")
    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("🛑 智能教案生成平台 (优化版) 关闭中...")
    # startup_manager 会自动处理关闭逻辑

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智能教案生成平台 API (优化版)",
        "version": "2.0.0",
        "port": settings.server.port,
        "docs": "/api/docs",
        "health": "/api/v1/health/health",
        "monitoring": "/api/v1/monitoring",
        "websocket": "/api/v1/ws/{user_id}",
        "export": "/api/v1/export/formats",
        "ai_management": "/api/v1/ai",
        "features": [
            "多AI服务支持 (Gemini, OpenAI, Claude) + 容错机制",
            "Cloudflare R2 存储 + 本地缓存",
            "实时WebSocket通知 + 连接管理",
            "多格式导出 + 批量处理",
            "异步文档处理 + 优先级队列",
            "多层缓存系统 (Redis + 本地)",
            "智能限流 + 请求优化",
            "高级监控 + 实时指标",
            "性能优化 + 响应压缩",
            "容错任务调度 + 依赖管理"
        ],
        "optimization_features": [
            "🚀 高性能API中间件",
            "📊 实时监控和告警",
            "🎯 智能任务调度",
            "💾 多层缓存优化",
            "🔧 自动故障恢复",
            "📈 性能指标收集",
            "⚡ 请求压缩和缓存",
            "🛡️ 智能限流保护"
        ]
    }

@app.get("/health")
async def health_check():
    """基础健康检查（兼容性端点）"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.debug,
        log_level="info"
    )

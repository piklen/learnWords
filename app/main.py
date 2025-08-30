from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from app.api.v1.api import api_router, websocket_router
from app.core.config import settings
from app.core.database import engine
from app.core.middleware import setup_middleware
from app.core.logging import setup_logging
from app.models import Base

# Setup logging
logger = setup_logging()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="智能教案生成平台",
    description="基于AI的智能教案生成系统",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

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
    logger.info("🚀 智能教案生成平台启动中...")
    logger.info(f"🌐 服务器地址: {settings.host}:{settings.port}")
    logger.info(f"📊 调试模式: {settings.debug}")
    logger.info(f"🔗 API前缀: {settings.api_prefix}")
    logger.info(f"📁 最大文件大小: {settings.max_file_size / (1024*1024):.1f}MB")
    logger.info(f"🌐 WebSocket支持: 已启用")
    logger.info(f"📤 导出功能: 已启用")
    logger.info(f"💾 缓存系统: 已启用")
    logger.info(f"🔒 权限管理: 已启用")
    logger.info(f"⚡ API限流: 已启用")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("🛑 智能教案生成平台关闭中...")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智能教案生成平台 API",
        "version": "1.0.0",
        "port": settings.port,
        "docs": "/api/docs",
        "health": "/api/v1/health/health",
        "websocket": "/api/v1/ws/{user_id}",
        "export": "/api/v1/export/formats",
        "ai_management": "/api/v1/ai",
        "features": [
            "多AI服务支持 (Gemini, OpenAI, Claude)",
            "Cloudflare R2 存储",
            "实时WebSocket通知",
            "多格式导出",
            "异步文档处理"
        ]
    }

@app.get("/health")
async def health_check():
    """基础健康检查（兼容性端点）"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )

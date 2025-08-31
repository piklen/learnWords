from fastapi import APIRouter
from app.api.v1.endpoints import auth, documents, lesson_plans, health, admin, websocket, export, ai_management, monitoring

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(lesson_plans.router, prefix="/lesson-plans", tags=["lesson plans"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(ai_management.router, prefix="/ai", tags=["ai management"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])

# WebSocket路由需要单独处理，因为它不是标准的HTTP路由
websocket_router = APIRouter()
websocket_router.include_router(websocket.router, tags=["websocket"])

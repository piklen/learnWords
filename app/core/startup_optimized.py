"""
优化的应用启动脚本
初始化所有优化组件和服务
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config_optimized import settings
from app.core.cache_optimized import cache
from app.core.monitoring import metrics_collector, request_metrics
from app.core.enhanced_task_scheduler import enhanced_scheduler
from app.core.performance_middleware import create_performance_middleware

logger = logging.getLogger(__name__)

class OptimizedStartupManager:
    """优化的启动管理器"""
    
    def __init__(self):
        self.components = []
        self.startup_tasks = []
        self.shutdown_tasks = []
    
    async def initialize_cache_system(self):
        """初始化缓存系统"""
        try:
            await cache.initialize()
            logger.info("✅ Cache system initialized")
            self.components.append("cache")
        except Exception as e:
            logger.error(f"❌ Failed to initialize cache system: {e}")
            raise
    
    async def initialize_monitoring(self):
        """初始化监控系统"""
        try:
            await metrics_collector.initialize()
            await request_metrics.initialize()
            
            # 启动指标收集
            collection_task = asyncio.create_task(metrics_collector.start_collection())
            self.startup_tasks.append(collection_task)
            
            logger.info("✅ Monitoring system initialized")
            self.components.append("monitoring")
        except Exception as e:
            logger.error(f"❌ Failed to initialize monitoring: {e}")
            # 监控失败不应该阻止应用启动
            logger.warning("Continuing without monitoring")
    
    async def initialize_task_scheduler(self):
        """初始化任务调度器"""
        try:
            await enhanced_scheduler.initialize()
            await enhanced_scheduler.start()
            
            logger.info("✅ Enhanced task scheduler initialized")
            self.components.append("task_scheduler")
        except Exception as e:
            logger.error(f"❌ Failed to initialize task scheduler: {e}")
            raise
    
    async def initialize_ai_services(self):
        """初始化AI服务"""
        try:
            from app.services.ai_service_optimized import ai_service
            
            # AI服务在导入时已初始化，这里只做健康检查
            health_check = await ai_service.health_check()
            available_providers = health_check.get("total_available", 0)
            
            if available_providers == 0:
                logger.warning("⚠️ No AI providers available, but continuing startup")
            else:
                logger.info(f"✅ AI services initialized with {available_providers} provider(s)")
            
            self.components.append("ai_services")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI services: {e}")
            # AI服务失败不应该阻止应用启动
            logger.warning("Continuing without AI services")
    
    async def verify_database_connection(self):
        """验证数据库连接"""
        try:
            from app.core.database_optimized import check_database_health, check_read_replica_health
            
            # 检查主数据库
            primary_health = await check_database_health()
            if primary_health["status"] != "healthy":
                raise Exception(f"Primary database unhealthy: {primary_health}")
            
            # 检查读副本（如果配置了）
            replica_health = await check_read_replica_health()
            if replica_health["status"] == "unhealthy":
                logger.warning("⚠️ Read replica unhealthy, but continuing with primary only")
            
            logger.info("✅ Database connections verified")
            self.components.append("database")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    async def validate_configuration(self):
        """验证配置"""
        try:
            # 检查必需配置
            missing_settings = settings.validate_required_settings()
            if missing_settings:
                logger.error(f"❌ Missing required settings: {missing_settings}")
                raise Exception(f"Missing required configuration: {missing_settings}")
            
            # 记录配置信息
            logger.info(f"✅ Configuration validated for {settings.server.environment} environment")
            logger.info(f"   - Database: {settings.database.database_url.split('@')[-1] if '@' in settings.database.database_url else 'configured'}")
            logger.info(f"   - Redis: {settings.redis.redis_url.split('@')[-1] if '@' in settings.redis.redis_url else 'configured'}")
            logger.info(f"   - AI Provider: {settings.ai.ai_provider}")
            logger.info(f"   - Storage Backend: {settings.storage.storage_backend}")
            
            self.components.append("configuration")
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            raise
    
    async def setup_error_handling(self):
        """设置错误处理"""
        try:
            # 配置日志级别
            if settings.server.debug:
                logging.getLogger().setLevel(logging.DEBUG)
                logger.info("✅ Debug logging enabled")
            else:
                logging.getLogger().setLevel(logging.INFO)
            
            self.components.append("error_handling")
        except Exception as e:
            logger.error(f"❌ Error handling setup failed: {e}")
            raise
    
    async def startup(self):
        """执行启动序列"""
        logger.info("🚀 Starting optimized application startup...")
        
        startup_steps = [
            ("Configuration Validation", self.validate_configuration),
            ("Error Handling Setup", self.setup_error_handling),
            ("Database Verification", self.verify_database_connection),
            ("Cache System", self.initialize_cache_system),
            ("Monitoring System", self.initialize_monitoring),
            ("Task Scheduler", self.initialize_task_scheduler),
            ("AI Services", self.initialize_ai_services),
        ]
        
        for step_name, step_func in startup_steps:
            try:
                logger.info(f"   Initializing {step_name}...")
                await step_func()
            except Exception as e:
                logger.error(f"   ❌ {step_name} initialization failed: {e}")
                # 某些组件失败可能不需要停止启动
                if step_name in ["Database Verification", "Configuration Validation"]:
                    raise
                else:
                    logger.warning(f"   ⚠️ Continuing without {step_name}")
        
        logger.info(f"✅ Application startup completed successfully!")
        logger.info(f"   Initialized components: {', '.join(self.components)}")
        
        # 记录启动指标
        await self._record_startup_metrics()
    
    async def shutdown(self):
        """执行关闭序列"""
        logger.info("🛑 Starting application shutdown...")
        
        # 停止后台任务
        for task in self.startup_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # 关闭组件
        if "task_scheduler" in self.components:
            try:
                await enhanced_scheduler.stop()
                logger.info("   ✅ Task scheduler stopped")
            except Exception as e:
                logger.error(f"   ❌ Task scheduler shutdown error: {e}")
        
        if "monitoring" in self.components:
            try:
                await metrics_collector.stop_collection()
                logger.info("   ✅ Monitoring stopped")
            except Exception as e:
                logger.error(f"   ❌ Monitoring shutdown error: {e}")
        
        logger.info("✅ Application shutdown completed")
    
    async def _record_startup_metrics(self):
        """记录启动指标"""
        try:
            startup_info = {
                "timestamp": "startup",
                "components_initialized": self.components,
                "environment": settings.server.environment,
                "debug_mode": settings.server.debug,
                "worker_concurrency": settings.tasks.worker_concurrency,
                "cache_enabled": "cache" in self.components,
                "monitoring_enabled": "monitoring" in self.components
            }
            
            # 这里可以发送到监控系统或记录到数据库
            logger.debug(f"Startup metrics: {startup_info}")
            
        except Exception as e:
            logger.error(f"Failed to record startup metrics: {e}")

# 全局启动管理器实例
startup_manager = OptimizedStartupManager()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI应用生命周期管理"""
    try:
        # 启动
        await startup_manager.startup()
        yield
    finally:
        # 关闭
        await startup_manager.shutdown()

def setup_optimized_app(app: FastAPI) -> FastAPI:
    """设置优化的FastAPI应用"""
    
    # 添加性能中间件
    app = create_performance_middleware(app)
    
    # 设置生命周期管理
    app.router.lifespan_context = lifespan
    
    # 添加启动事件（如果不使用lifespan）
    @app.on_event("startup")
    async def startup_event():
        if not hasattr(app, "_startup_completed"):
            await startup_manager.startup()
            app._startup_completed = True
    
    @app.on_event("shutdown")
    async def shutdown_event():
        await startup_manager.shutdown()
    
    # 添加健康检查中间件
    @app.middleware("http")
    async def health_check_middleware(request, call_next):
        # 记录请求指标
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        if hasattr(request_metrics, 'record_request'):
            asyncio.create_task(
                request_metrics.record_request(
                    request.method,
                    str(request.url.path),
                    response.status_code,
                    process_time
                )
            )
        
        return response
    
    return app


# 便捷函数
async def verify_system_health() -> dict:
    """验证系统健康状态"""
    health_status = {
        "overall": "healthy",
        "components": {},
        "issues": []
    }
    
    # 检查各个组件
    components_to_check = [
        ("database", lambda: check_database_health()),
        ("cache", lambda: cache.get_stats()),
        ("ai_services", lambda: ai_service.health_check()),
    ]
    
    for component_name, check_func in components_to_check:
        try:
            if component_name in startup_manager.components:
                result = await check_func()
                health_status["components"][component_name] = {
                    "status": "healthy",
                    "details": result
                }
            else:
                health_status["components"][component_name] = {
                    "status": "not_initialized"
                }
        except Exception as e:
            health_status["components"][component_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["issues"].append(f"{component_name}: {str(e)}")
    
    # 确定整体状态
    if health_status["issues"]:
        health_status["overall"] = "degraded"
    
    return health_status

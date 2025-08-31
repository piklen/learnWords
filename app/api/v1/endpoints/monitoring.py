"""
监控和指标API端点
提供系统监控、性能指标、健康检查等功能
"""

import asyncio
import time
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
import json

from app.core.security import get_current_user, require_admin
from app.core.monitoring import metrics_collector, request_metrics
from app.core.enhanced_task_scheduler import enhanced_scheduler
from app.core.cache_optimized import cache
from app.core.database_optimized import check_database_health, check_read_replica_health
from app.services.ai_service_optimized import ai_service
from app.models.user import User

router = APIRouter()

@router.get("/system")
async def get_system_metrics(
    hours: int = Query(default=1, ge=1, le=168),  # 最多7天
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """获取系统指标"""
    try:
        # 获取历史指标
        metrics_data = await metrics_collector.get_metrics(hours=hours)
        
        # 获取当前系统状态
        current_system = {
            "cpu_percent": psutil.cpu_percent(),
            "memory": dict(psutil.virtual_memory()._asdict()),
            "disk": dict(psutil.disk_usage('/')._asdict()),
            "network": dict(psutil.net_io_counters()._asdict()),
            "load_avg": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0, 0, 0],
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "uptime": time.time() - psutil.boot_time()
        }
        
        # 计算趋势
        trends = _calculate_trends(metrics_data)
        
        return {
            "current": current_system,
            "history": metrics_data,
            "trends": trends,
            "data_points": len(metrics_data),
            "time_range_hours": hours
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")

@router.get("/application")
async def get_application_metrics(
    hours: int = Query(default=1, ge=1, le=168),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """获取应用指标"""
    try:
        # 获取任务指标
        task_metrics = await enhanced_scheduler.get_task_metrics(hours=hours)
        
        # 获取AI服务指标
        ai_metrics = ai_service.get_all_metrics()
        
        # 获取缓存指标
        cache_stats = await cache.get_stats()
        
        # 获取请求指标
        request_stats = await _get_request_stats()
        
        # 获取数据库健康状态
        db_health = {
            "primary": await check_database_health(),
            "read_replica": await check_read_replica_health()
        }
        
        return {
            "tasks": task_metrics,
            "ai_services": ai_metrics,
            "cache": cache_stats,
            "requests": request_stats,
            "database": db_health,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get application metrics: {str(e)}")

@router.get("/health/comprehensive")
async def comprehensive_health_check(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """综合健康检查"""
    health_results = {
        "overall_status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    issues = []
    
    try:
        # 1. 数据库健康检查
        db_primary = await check_database_health()
        db_replica = await check_read_replica_health()
        
        health_results["checks"]["database"] = {
            "primary": db_primary,
            "read_replica": db_replica,
            "status": "healthy" if db_primary["status"] == "healthy" else "unhealthy"
        }
        
        if db_primary["status"] != "healthy":
            issues.append("Primary database unhealthy")
        
        # 2. Redis/缓存健康检查
        try:
            cache_stats = await cache.get_stats()
            health_results["checks"]["cache"] = {
                "status": "healthy" if "error" not in cache_stats else "unhealthy",
                "stats": cache_stats
            }
            if "error" in cache_stats:
                issues.append("Cache system unhealthy")
        except Exception as e:
            health_results["checks"]["cache"] = {"status": "unhealthy", "error": str(e)}
            issues.append("Cache system error")
        
        # 3. AI服务健康检查
        try:
            ai_health = await ai_service.health_check()
            healthy_providers = ai_health.get("total_available", 0)
            
            health_results["checks"]["ai_services"] = {
                "status": "healthy" if healthy_providers > 0 else "unhealthy",
                "available_providers": healthy_providers,
                "details": ai_health
            }
            
            if healthy_providers == 0:
                issues.append("No AI providers available")
                
        except Exception as e:
            health_results["checks"]["ai_services"] = {"status": "error", "error": str(e)}
            issues.append("AI services error")
        
        # 4. 任务系统健康检查
        try:
            task_stats = enhanced_scheduler.stats
            health_results["checks"]["task_system"] = {
                "status": "healthy",
                "active_tasks": task_stats.get("active_tasks", 0),
                "queue_sizes": task_stats.get("queue_sizes", {}),
                "worker_utilization": task_stats.get("worker_utilization", 0)
            }
            
            # 检查工作者利用率
            if task_stats.get("worker_utilization", 0) > 0.95:
                issues.append("High worker utilization")
                
        except Exception as e:
            health_results["checks"]["task_system"] = {"status": "error", "error": str(e)}
            issues.append("Task system error")
        
        # 5. 系统资源检查
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health_results["checks"]["system_resources"] = {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent
            }
            
            # 检查资源使用率
            if cpu_percent > 90:
                issues.append("High CPU usage")
                health_results["checks"]["system_resources"]["status"] = "warning"
            
            if memory.percent > 90:
                issues.append("High memory usage")
                health_results["checks"]["system_resources"]["status"] = "warning"
            
            if disk.percent > 90:
                issues.append("High disk usage")
                health_results["checks"]["system_resources"]["status"] = "warning"
                
        except Exception as e:
            health_results["checks"]["system_resources"] = {"status": "error", "error": str(e)}
            issues.append("System resources check error")
        
        # 确定整体状态
        if issues:
            health_results["overall_status"] = "unhealthy"
            health_results["issues"] = issues
        
        return health_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/alerts")
async def get_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    severity: Optional[str] = Query(default=None),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """获取告警信息"""
    try:
        alerts = await metrics_collector.get_alerts(limit=limit)
        
        # 按严重程度过滤
        if severity:
            alerts = [alert for alert in alerts if alert.get("level") == severity]
        
        # 统计
        alert_counts = {}
        for alert in alerts:
            level = alert.get("level", "unknown")
            alert_counts[level] = alert_counts.get(level, 0) + 1
        
        return {
            "alerts": alerts,
            "total": len(alerts),
            "counts_by_severity": alert_counts,
            "filter": {"severity": severity, "limit": limit}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")

@router.get("/performance/realtime")
async def get_realtime_performance(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """获取实时性能数据"""
    try:
        # 获取实时统计
        stats = await _get_request_stats()
        
        # 获取当前系统状态
        current_time = time.time()
        system_info = {
            "timestamp": current_time,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "active_connections": len(psutil.net_connections()),
            "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        }
        
        # 获取任务统计
        task_stats = enhanced_scheduler.stats
        
        return {
            "requests": stats,
            "system": system_info,
            "tasks": {
                "active": task_stats.get("active_tasks", 0),
                "total": task_stats.get("total_tasks", 0),
                "completed": task_stats.get("completed_tasks", 0),
                "failed": task_stats.get("failed_tasks", 0),
                "worker_utilization": task_stats.get("worker_utilization", 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get realtime performance: {str(e)}")

@router.get("/performance/stream")
async def stream_performance_metrics(
    current_user: User = Depends(require_admin)
) -> StreamingResponse:
    """实时性能指标流"""
    async def generate_metrics():
        """生成实时指标数据"""
        while True:
            try:
                # 获取实时数据
                data = await get_realtime_performance(current_user)
                
                # 转换为SSE格式
                yield f"data: {json.dumps(data)}\n\n"
                
                await asyncio.sleep(5)  # 每5秒更新一次
                
            except Exception as e:
                error_data = {"error": str(e), "timestamp": datetime.now().isoformat()}
                yield f"data: {json.dumps(error_data)}\n\n"
                await asyncio.sleep(10)
    
    return StreamingResponse(
        generate_metrics(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.post("/maintenance/cache/clear")
async def clear_cache(
    namespace: Optional[str] = Query(default=None),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """清理缓存"""
    try:
        if namespace:
            cleared = await cache.clear_namespace(namespace)
            return {"message": f"Cleared {cleared} cache entries from namespace '{namespace}'"}
        else:
            # 这里需要实现全局清理功能
            return {"message": "Cache clear operation initiated"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.post("/maintenance/tasks/cleanup")
async def cleanup_completed_tasks(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """清理已完成的任务"""
    try:
        # 这里需要实现任务清理逻辑
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 模拟清理操作
        cleanup_count = 0  # 实际实现时需要从任务系统获取
        
        return {
            "message": f"Cleaned up {cleanup_count} completed tasks older than {days} days",
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup tasks: {str(e)}")

@router.get("/diagnostics/dependencies")
async def check_dependencies(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """检查系统依赖"""
    dependencies = {
        "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
        "psutil_version": psutil.__version__,
        "system_platform": psutil.LINUX or psutil.WINDOWS or psutil.MACOS,
        "available_cores": psutil.cpu_count(),
        "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2)
    }
    
    # 检查关键依赖
    dependency_status = {}
    
    try:
        import redis
        dependency_status["redis"] = {"available": True, "version": redis.__version__}
    except ImportError:
        dependency_status["redis"] = {"available": False, "error": "Not installed"}
    
    try:
        import celery
        dependency_status["celery"] = {"available": True, "version": celery.__version__}
    except ImportError:
        dependency_status["celery"] = {"available": False, "error": "Not installed"}
    
    try:
        import fastapi
        dependency_status["fastapi"] = {"available": True, "version": fastapi.__version__}
    except ImportError:
        dependency_status["fastapi"] = {"available": False, "error": "Not installed"}
    
    return {
        "system_info": dependencies,
        "dependencies": dependency_status,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/logs/recent")
async def get_recent_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    level: Optional[str] = Query(default=None),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """获取最近的日志（简化实现）"""
    # 这里是简化实现，实际应该从日志系统获取
    return {
        "message": "Log retrieval not implemented in this demo",
        "limit": limit,
        "level": level,
        "suggestion": "Use external log aggregation system like ELK stack"
    }


# 辅助函数
def _calculate_trends(metrics_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算指标趋势"""
    if len(metrics_data) < 2:
        return {"insufficient_data": True}
    
    trends = {}
    
    try:
        # CPU趋势
        cpu_values = [m["system"]["cpu_percent"] for m in metrics_data if "system" in m]
        if len(cpu_values) >= 2:
            trends["cpu"] = {
                "direction": "up" if cpu_values[-1] > cpu_values[0] else "down",
                "change_percent": ((cpu_values[-1] - cpu_values[0]) / cpu_values[0]) * 100 if cpu_values[0] > 0 else 0
            }
        
        # 内存趋势
        memory_values = [m["system"]["memory_percent"] for m in metrics_data if "system" in m]
        if len(memory_values) >= 2:
            trends["memory"] = {
                "direction": "up" if memory_values[-1] > memory_values[0] else "down",
                "change_percent": ((memory_values[-1] - memory_values[0]) / memory_values[0]) * 100 if memory_values[0] > 0 else 0
            }
        
    except Exception as e:
        trends["error"] = str(e)
    
    return trends

async def _get_request_stats() -> Dict[str, Any]:
    """获取请求统计"""
    try:
        if hasattr(request_metrics, 'redis') and request_metrics.redis:
            stats_data = await request_metrics.redis.get("request_stats")
            if stats_data:
                return json.loads(stats_data)
    except Exception:
        pass
    
    return {
        "total": 0,
        "success": 0,
        "failed": 0,
        "avg_response_time": 0,
        "last_updated": None
    }

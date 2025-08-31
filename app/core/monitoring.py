import asyncio
import logging
import time
import psutil
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int
    load_average: List[float]

@dataclass
class ApplicationMetrics:
    """应用指标"""
    timestamp: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    ai_api_calls: int
    ai_api_failures: int
    storage_operations: int
    cache_hits: int
    cache_misses: int
    websocket_connections: int

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.redis = None
        self.metrics_key = "learnwords:metrics"
        self.alerts_key = "learnwords:alerts"
        self.collection_interval = 60  # 每分钟收集一次
        self._collecting = False
        self._last_network_stats = None
        
    async def initialize(self):
        """初始化Redis连接"""
        try:
            self.redis = redis.Redis.from_url(settings.redis_url)
            await self.redis.ping()
            logger.info("Metrics collector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize metrics collector: {e}")
            self.redis = None
    
    async def start_collection(self):
        """开始指标收集"""
        if self._collecting:
            return
        
        self._collecting = True
        logger.info("Starting metrics collection")
        
        while self._collecting:
            try:
                # 收集系统指标
                system_metrics = await self._collect_system_metrics()
                
                # 收集应用指标
                app_metrics = await self._collect_application_metrics()
                
                # 保存指标
                await self._save_metrics(system_metrics, app_metrics)
                
                # 检查告警
                await self._check_alerts(system_metrics, app_metrics)
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            await asyncio.sleep(self.collection_interval)
    
    async def stop_collection(self):
        """停止指标收集"""
        self._collecting = False
        logger.info("Stopped metrics collection")
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存
        memory = psutil.virtual_memory()
        
        # 磁盘
        disk = psutil.disk_usage('/')
        
        # 网络
        network = psutil.net_io_counters()
        network_sent_mb = 0
        network_recv_mb = 0
        
        if self._last_network_stats:
            network_sent_mb = (network.bytes_sent - self._last_network_stats.bytes_sent) / 1024 / 1024
            network_recv_mb = (network.bytes_recv - self._last_network_stats.bytes_recv) / 1024 / 1024
        
        self._last_network_stats = network
        
        # 负载平均值
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        
        # 活跃连接数
        active_connections = len(psutil.net_connections())
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            memory_available_mb=memory.available / 1024 / 1024,
            disk_usage_percent=disk.percent,
            disk_used_gb=disk.used / 1024 / 1024 / 1024,
            disk_free_gb=disk.free / 1024 / 1024 / 1024,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            active_connections=active_connections,
            load_average=list(load_avg)
        )
    
    async def _collect_application_metrics(self) -> ApplicationMetrics:
        """收集应用指标"""
        if not self.redis:
            return ApplicationMetrics(
                timestamp=datetime.now(),
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time=0,
                active_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                ai_api_calls=0,
                ai_api_failures=0,
                storage_operations=0,
                cache_hits=0,
                cache_misses=0,
                websocket_connections=0
            )
        
        try:
            # 从各个服务收集指标
            request_stats = await self._get_request_stats()
            task_stats = await self._get_task_stats()
            ai_stats = await self._get_ai_stats()
            cache_stats = await self._get_cache_stats()
            websocket_stats = await self._get_websocket_stats()
            
            return ApplicationMetrics(
                timestamp=datetime.now(),
                total_requests=request_stats.get('total', 0),
                successful_requests=request_stats.get('success', 0),
                failed_requests=request_stats.get('failed', 0),
                avg_response_time=request_stats.get('avg_response_time', 0),
                active_tasks=task_stats.get('active', 0),
                completed_tasks=task_stats.get('completed', 0),
                failed_tasks=task_stats.get('failed', 0),
                ai_api_calls=ai_stats.get('total_calls', 0),
                ai_api_failures=ai_stats.get('failures', 0),
                storage_operations=0,  # TODO: 实现存储操作统计
                cache_hits=cache_stats.get('hits', 0),
                cache_misses=cache_stats.get('misses', 0),
                websocket_connections=websocket_stats.get('active_connections', 0)
            )
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            return ApplicationMetrics(
                timestamp=datetime.now(),
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time=0,
                active_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                ai_api_calls=0,
                ai_api_failures=0,
                storage_operations=0,
                cache_hits=0,
                cache_misses=0,
                websocket_connections=0
            )
    
    async def _get_request_stats(self) -> Dict[str, Any]:
        """获取请求统计"""
        try:
            stats_data = await self.redis.get("request_stats")
            return json.loads(stats_data) if stats_data else {}
        except Exception:
            return {}
    
    async def _get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计"""
        try:
            from app.core.task_manager import task_manager
            metrics = await task_manager.get_task_metrics(hours=1)
            return {
                'active': 0,  # TODO: 实现活跃任务统计
                'completed': metrics.get('successful_tasks', 0),
                'failed': metrics.get('failed_tasks', 0)
            }
        except Exception:
            return {'active': 0, 'completed': 0, 'failed': 0}
    
    async def _get_ai_stats(self) -> Dict[str, Any]:
        """获取AI服务统计"""
        try:
            from app.services.ai_service_optimized import ai_service
            metrics = ai_service.get_all_metrics()
            
            total_calls = 0
            failures = 0
            
            for provider_metrics in metrics.values():
                total_calls += provider_metrics.get('total_requests', 0)
                failures += provider_metrics.get('failure_count', 0)
            
            return {
                'total_calls': total_calls,
                'failures': failures
            }
        except Exception:
            return {'total_calls': 0, 'failures': 0}
    
    async def _get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            from app.core.cache_optimized import cache
            stats = await cache.get_stats()
            return {
                'hits': stats.get('local_hit', 0) + stats.get('redis_hit', 0),
                'misses': stats.get('miss', 0)
            }
        except Exception:
            return {'hits': 0, 'misses': 0}
    
    async def _get_websocket_stats(self) -> Dict[str, Any]:
        """获取WebSocket统计"""
        try:
            # TODO: 从WebSocket连接管理器获取统计
            return {'active_connections': 0}
        except Exception:
            return {'active_connections': 0}
    
    async def _save_metrics(self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics):
        """保存指标到Redis"""
        if not self.redis:
            return
        
        try:
            # 准备指标数据
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'system': asdict(system_metrics),
                'application': asdict(app_metrics)
            }
            
            # 转换datetime对象为字符串
            metrics_data['system']['timestamp'] = system_metrics.timestamp.isoformat()
            metrics_data['application']['timestamp'] = app_metrics.timestamp.isoformat()
            
            # 保存到Redis列表（时间序列）
            await self.redis.lpush(self.metrics_key, json.dumps(metrics_data))
            
            # 只保留最近24小时的数据
            await self.redis.ltrim(self.metrics_key, 0, 1440)  # 24小时 * 60分钟
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    async def _check_alerts(self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics):
        """检查告警条件"""
        alerts = []
        
        # CPU告警
        if system_metrics.cpu_percent > 80:
            alerts.append({
                'type': 'cpu_high',
                'level': 'warning' if system_metrics.cpu_percent < 90 else 'critical',
                'message': f'High CPU usage: {system_metrics.cpu_percent:.1f}%',
                'value': system_metrics.cpu_percent
            })
        
        # 内存告警
        if system_metrics.memory_percent > 80:
            alerts.append({
                'type': 'memory_high',
                'level': 'warning' if system_metrics.memory_percent < 90 else 'critical',
                'message': f'High memory usage: {system_metrics.memory_percent:.1f}%',
                'value': system_metrics.memory_percent
            })
        
        # 磁盘告警
        if system_metrics.disk_usage_percent > 85:
            alerts.append({
                'type': 'disk_high',
                'level': 'warning' if system_metrics.disk_usage_percent < 95 else 'critical',
                'message': f'High disk usage: {system_metrics.disk_usage_percent:.1f}%',
                'value': system_metrics.disk_usage_percent
            })
        
        # 任务失败率告警
        total_tasks = app_metrics.completed_tasks + app_metrics.failed_tasks
        if total_tasks > 0:
            failure_rate = app_metrics.failed_tasks / total_tasks
            if failure_rate > 0.1:  # 10%失败率
                alerts.append({
                    'type': 'high_task_failure_rate',
                    'level': 'warning' if failure_rate < 0.2 else 'critical',
                    'message': f'High task failure rate: {failure_rate:.1%}',
                    'value': failure_rate
                })
        
        # AI API失败率告警
        if app_metrics.ai_api_calls > 0:
            ai_failure_rate = app_metrics.ai_api_failures / app_metrics.ai_api_calls
            if ai_failure_rate > 0.05:  # 5%失败率
                alerts.append({
                    'type': 'high_ai_failure_rate',
                    'level': 'warning' if ai_failure_rate < 0.1 else 'critical',
                    'message': f'High AI API failure rate: {ai_failure_rate:.1%}',
                    'value': ai_failure_rate
                })
        
        # 保存告警
        if alerts:
            await self._save_alerts(alerts)
    
    async def _save_alerts(self, alerts: List[Dict[str, Any]]):
        """保存告警信息"""
        if not self.redis:
            return
        
        try:
            for alert in alerts:
                alert['timestamp'] = datetime.now().isoformat()
                alert['id'] = f"{alert['type']}_{int(time.time())}"
                
                await self.redis.lpush(self.alerts_key, json.dumps(alert))
                
                # 记录日志
                level = logging.WARNING if alert['level'] == 'warning' else logging.ERROR
                logger.log(level, f"ALERT: {alert['message']}")
            
            # 只保留最近100个告警
            await self.redis.ltrim(self.alerts_key, 0, 99)
            
        except Exception as e:
            logger.error(f"Failed to save alerts: {e}")
    
    async def get_metrics(self, hours: int = 1) -> List[Dict[str, Any]]:
        """获取指标数据"""
        if not self.redis:
            return []
        
        try:
            # 计算需要获取的数据点数量
            points = hours * 60  # 每分钟一个数据点
            
            metrics_data = await self.redis.lrange(self.metrics_key, 0, points - 1)
            
            result = []
            for data in metrics_data:
                try:
                    parsed_data = json.loads(data)
                    result.append(parsed_data)
                except json.JSONDecodeError:
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    async def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取告警信息"""
        if not self.redis:
            return []
        
        try:
            alerts_data = await self.redis.lrange(self.alerts_key, 0, limit - 1)
            
            result = []
            for data in alerts_data:
                try:
                    parsed_data = json.loads(data)
                    result.append(parsed_data)
                except json.JSONDecodeError:
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

# 全局指标收集器实例
metrics_collector = MetricsCollector()

# 请求指标中间件
class MetricsMiddleware:
    """请求指标中间件"""
    
    def __init__(self):
        self.redis = None
        self.stats_key = "request_stats"
    
    async def initialize(self):
        """初始化Redis连接"""
        try:
            self.redis = redis.Redis.from_url(settings.redis_url)
        except Exception as e:
            logger.error(f"Failed to initialize metrics middleware: {e}")
    
    async def record_request(self, method: str, path: str, status_code: int, response_time: float):
        """记录请求指标"""
        if not self.redis:
            return
        
        try:
            # 获取当前统计
            stats_data = await self.redis.get(self.stats_key)
            stats = json.loads(stats_data) if stats_data else {
                'total': 0,
                'success': 0,
                'failed': 0,
                'response_times': [],
                'last_updated': None
            }
            
            # 更新统计
            stats['total'] += 1
            if 200 <= status_code < 400:
                stats['success'] += 1
            else:
                stats['failed'] += 1
            
            # 记录响应时间（保留最近100个）
            stats['response_times'].append(response_time)
            if len(stats['response_times']) > 100:
                stats['response_times'] = stats['response_times'][-100:]
            
            # 计算平均响应时间
            stats['avg_response_time'] = sum(stats['response_times']) / len(stats['response_times'])
            stats['last_updated'] = datetime.now().isoformat()
            
            # 保存统计
            await self.redis.setex(self.stats_key, 3600, json.dumps(stats))
            
        except Exception as e:
            logger.error(f"Failed to record request metrics: {e}")

# 全局请求指标中间件实例
request_metrics = MetricsMiddleware()

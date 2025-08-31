import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid
from contextlib import asynccontextmanager

from celery import Celery
from celery.result import AsyncResult
from celery.signals import task_prerun, task_postrun, task_failure
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"

class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class TaskInfo:
    """任务信息"""
    id: str
    name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.NORMAL
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None

class TaskManager:
    """优化的任务管理器"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.redis_url)
        self.task_info_key = "task_info:{}"
        self.task_queue_key = "task_queue:{}"
        self.task_metrics_key = "task_metrics"
        
    async def create_task(
        self,
        task_name: str,
        task_args: tuple = (),
        task_kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        metadata: dict = None
    ) -> str:
        """创建任务"""
        task_id = str(uuid.uuid4())
        task_kwargs = task_kwargs or {}
        metadata = metadata or {}
        
        task_info = TaskInfo(
            id=task_id,
            name=task_name,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            priority=priority,
            max_retries=max_retries,
            metadata=metadata
        )
        
        # 保存任务信息
        await self._save_task_info(task_info)
        
        # 根据优先级添加到队列
        queue_name = f"queue_{priority.name.lower()}"
        
        # 提交到Celery
        try:
            from app.celery_app import celery_app
            celery_result = celery_app.send_task(
                task_name,
                args=task_args,
                kwargs=task_kwargs,
                task_id=task_id,
                queue=queue_name,
                priority=priority.value
            )
            
            logger.info(f"Task {task_id} ({task_name}) created with priority {priority.name}")
            return task_id
            
        except Exception as e:
            task_info.status = TaskStatus.FAILURE
            task_info.error = f"Failed to submit task: {str(e)}"
            await self._save_task_info(task_info)
            raise
    
    async def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        try:
            data = self.redis_client.get(self.task_info_key.format(task_id))
            if data:
                task_data = json.loads(data)
                # 转换日期字符串回datetime对象
                for field in ['created_at', 'started_at', 'completed_at']:
                    if task_data.get(field):
                        task_data[field] = datetime.fromisoformat(task_data[field])
                
                task_data['status'] = TaskStatus(task_data['status'])
                task_data['priority'] = TaskPriority(task_data['priority'])
                
                return TaskInfo(**task_data)
        except Exception as e:
            logger.error(f"Failed to get task info {task_id}: {e}")
        return None
    
    async def update_task_progress(self, task_id: str, progress: float, message: str = None):
        """更新任务进度"""
        task_info = await self.get_task_info(task_id)
        if task_info:
            task_info.progress = max(0, min(100, progress))
            if message:
                task_info.metadata = task_info.metadata or {}
                task_info.metadata['progress_message'] = message
            await self._save_task_info(task_info)
    
    async def mark_task_started(self, task_id: str):
        """标记任务开始"""
        task_info = await self.get_task_info(task_id)
        if task_info:
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = datetime.now()
            await self._save_task_info(task_info)
    
    async def mark_task_completed(self, task_id: str, result: Any = None):
        """标记任务完成"""
        task_info = await self.get_task_info(task_id)
        if task_info:
            task_info.status = TaskStatus.SUCCESS
            task_info.completed_at = datetime.now()
            task_info.progress = 100.0
            task_info.result = result
            await self._save_task_info(task_info)
            await self._record_task_metrics(task_info)
    
    async def mark_task_failed(self, task_id: str, error: str):
        """标记任务失败"""
        task_info = await self.get_task_info(task_id)
        if task_info:
            task_info.status = TaskStatus.FAILURE
            task_info.completed_at = datetime.now()
            task_info.error = error
            await self._save_task_info(task_info)
            await self._record_task_metrics(task_info)
    
    async def retry_task(self, task_id: str) -> bool:
        """重试任务"""
        task_info = await self.get_task_info(task_id)
        if not task_info:
            return False
        
        if task_info.retries >= task_info.max_retries:
            logger.warning(f"Task {task_id} has exceeded max retries")
            return False
        
        task_info.retries += 1
        task_info.status = TaskStatus.RETRY
        task_info.started_at = None
        task_info.completed_at = None
        task_info.progress = 0.0
        task_info.error = None
        
        await self._save_task_info(task_info)
        
        # 重新提交任务
        try:
            from app.celery_app import celery_app
            celery_app.send_task(
                task_info.name,
                task_id=task_id,
                queue=f"queue_{task_info.priority.name.lower()}",
                priority=task_info.priority.value,
                retry=True
            )
            return True
        except Exception as e:
            await self.mark_task_failed(task_id, f"Retry failed: {str(e)}")
            return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            from app.celery_app import celery_app
            celery_app.control.revoke(task_id, terminate=True)
            
            task_info = await self.get_task_info(task_id)
            if task_info:
                task_info.status = TaskStatus.REVOKED
                task_info.completed_at = datetime.now()
                await self._save_task_info(task_info)
            
            return True
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    async def get_task_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """获取任务指标"""
        try:
            metrics_data = self.redis_client.get(self.task_metrics_key)
            if not metrics_data:
                return self._get_empty_metrics()
            
            metrics = json.loads(metrics_data)
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # 过滤最近的指标
            recent_metrics = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "avg_duration": 0,
                "task_types": {}
            }
            
            for metric in metrics.get('task_history', []):
                created_at = datetime.fromisoformat(metric['created_at'])
                if created_at > cutoff_time:
                    recent_metrics["total_tasks"] += 1
                    if metric['status'] == TaskStatus.SUCCESS.value:
                        recent_metrics["successful_tasks"] += 1
                    elif metric['status'] == TaskStatus.FAILURE.value:
                        recent_metrics["failed_tasks"] += 1
                    
                    # 记录任务类型
                    task_type = metric['task_name']
                    if task_type not in recent_metrics["task_types"]:
                        recent_metrics["task_types"][task_type] = {"count": 0, "avg_duration": 0}
                    recent_metrics["task_types"][task_type]["count"] += 1
            
            # 计算成功率
            if recent_metrics["total_tasks"] > 0:
                recent_metrics["success_rate"] = recent_metrics["successful_tasks"] / recent_metrics["total_tasks"]
            else:
                recent_metrics["success_rate"] = 0
            
            return recent_metrics
            
        except Exception as e:
            logger.error(f"Failed to get task metrics: {e}")
            return self._get_empty_metrics()
    
    async def _save_task_info(self, task_info: TaskInfo):
        """保存任务信息到Redis"""
        try:
            # 转换datetime对象为字符串
            task_data = asdict(task_info)
            for field in ['created_at', 'started_at', 'completed_at']:
                if task_data[field]:
                    task_data[field] = task_data[field].isoformat()
            
            task_data['status'] = task_info.status.value
            task_data['priority'] = task_info.priority.value
            
            self.redis_client.setex(
                self.task_info_key.format(task_info.id),
                timedelta(days=7),  # 保存7天
                json.dumps(task_data, default=str)
            )
        except Exception as e:
            logger.error(f"Failed to save task info {task_info.id}: {e}")
    
    async def _record_task_metrics(self, task_info: TaskInfo):
        """记录任务指标"""
        try:
            metrics_data = self.redis_client.get(self.task_metrics_key)
            metrics = json.loads(metrics_data) if metrics_data else {"task_history": []}
            
            duration = 0
            if task_info.started_at and task_info.completed_at:
                duration = (task_info.completed_at - task_info.started_at).total_seconds()
            
            metric = {
                "task_id": task_info.id,
                "task_name": task_info.name,
                "status": task_info.status.value,
                "created_at": task_info.created_at.isoformat(),
                "duration": duration,
                "retries": task_info.retries
            }
            
            metrics["task_history"].append(metric)
            
            # 保持最近1000条记录
            if len(metrics["task_history"]) > 1000:
                metrics["task_history"] = metrics["task_history"][-1000:]
            
            self.redis_client.setex(
                self.task_metrics_key,
                timedelta(days=30),  # 保存30天
                json.dumps(metrics)
            )
            
        except Exception as e:
            logger.error(f"Failed to record task metrics: {e}")
    
    def _get_empty_metrics(self) -> Dict[str, Any]:
        """获取空的指标对象"""
        return {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "success_rate": 0,
            "avg_duration": 0,
            "task_types": {}
        }

# 全局任务管理器实例
task_manager = TaskManager()

# Celery信号处理器
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """任务开始前的处理"""
    asyncio.create_task(task_manager.mark_task_started(task_id))

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """任务完成后的处理"""
    if state == 'SUCCESS':
        asyncio.create_task(task_manager.mark_task_completed(task_id, retval))

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """任务失败的处理"""
    asyncio.create_task(task_manager.mark_task_failed(task_id, str(exception)))

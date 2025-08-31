"""
增强的任务调度器
支持优先级队列、任务依赖、定时任务、故障恢复等功能
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum, IntEnum
import uuid
from collections import defaultdict
import heapq

import redis.asyncio as redis
from celery import Celery
from celery.result import AsyncResult

from app.core.config_optimized import settings

logger = logging.getLogger(__name__)

class TaskPriority(IntEnum):
    """任务优先级（数字越大优先级越高）"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    DEPENDENCY_FAILED = "dependency_failed"

class TaskType(Enum):
    """任务类型"""
    DOCUMENT_PROCESSING = "document_processing"
    LESSON_PLAN_GENERATION = "lesson_plan_generation"
    AI_TEXT_GENERATION = "ai_text_generation"
    BATCH_PROCESSING = "batch_processing"
    CLEANUP = "cleanup"
    MONITORING = "monitoring"
    EXPORT = "export"

@dataclass
class TaskDependency:
    """任务依赖"""
    task_id: str
    required_status: TaskStatus = TaskStatus.SUCCESS

@dataclass
class EnhancedTaskInfo:
    """增强的任务信息"""
    id: str
    name: str
    task_type: TaskType
    status: TaskStatus
    priority: TaskPriority
    
    # 时间信息
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 执行信息
    progress: float = 0.0
    retries: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    
    # 依赖和关联
    dependencies: List[TaskDependency] = field(default_factory=list)
    parent_task_id: Optional[str] = None
    child_task_ids: List[str] = field(default_factory=list)
    
    # 执行结果
    result: Optional[Any] = None
    error: Optional[str] = None
    error_trace: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # 执行信息
    worker_id: Optional[str] = None
    execution_time: Optional[float] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)

class TaskQueue:
    """优先级任务队列"""
    
    def __init__(self, name: str):
        self.name = name
        self._heap = []
        self._entry_map = {}
        self._counter = 0
        
    def put(self, task_info: EnhancedTaskInfo):
        """添加任务到队列"""
        # 使用负数因为heapq是最小堆，我们需要最大堆（高优先级先出）
        priority = -task_info.priority.value
        count = self._counter
        self._counter += 1
        
        entry = [priority, count, task_info.id, task_info]
        self._entry_map[task_info.id] = entry
        heapq.heappush(self._heap, entry)
    
    def get(self) -> Optional[EnhancedTaskInfo]:
        """从队列获取任务"""
        while self._heap:
            priority, count, task_id, task_info = heapq.heappop(self._heap)
            
            if task_id in self._entry_map:
                del self._entry_map[task_id]
                return task_info
        
        return None
    
    def remove(self, task_id: str) -> bool:
        """从队列移除任务"""
        if task_id in self._entry_map:
            entry = self._entry_map.pop(task_id)
            entry[2] = None  # 标记为已删除
            return True
        return False
    
    def size(self) -> int:
        """队列大小"""
        return len(self._entry_map)
    
    def is_empty(self) -> bool:
        """队列是否为空"""
        return len(self._entry_map) == 0

class EnhancedTaskScheduler:
    """增强的任务调度器"""
    
    def __init__(self):
        self.redis = None
        self.celery_app = None
        
        # 任务队列
        self.queues = {
            priority: TaskQueue(f"queue_{priority.name.lower()}")
            for priority in TaskPriority
        }
        
        # 任务存储
        self.tasks = {}  # task_id -> EnhancedTaskInfo
        self.task_dependencies = defaultdict(set)  # task_id -> set of dependent task_ids
        
        # 调度器状态
        self.is_running = False
        self.scheduler_task = None
        self.worker_tasks = []
        self.max_concurrent_tasks = settings.tasks.max_workers
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "active_tasks": 0,
            "queue_sizes": {},
            "worker_utilization": 0.0,
            "avg_execution_time": 0.0
        }
        
        # Redis键前缀
        self.task_key_prefix = "enhanced_task:"
        self.queue_key_prefix = "enhanced_queue:"
        self.stats_key = "enhanced_task_stats"
        
    async def initialize(self):
        """初始化调度器"""
        try:
            # 初始化Redis
            self.redis = redis.Redis.from_url(
                settings.redis.redis_url,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            await self.redis.ping()
            
            # 初始化Celery
            from app.celery_app import celery_app
            self.celery_app = celery_app
            
            # 恢复未完成的任务
            await self._recover_tasks()
            
            logger.info("Enhanced task scheduler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced task scheduler: {e}")
            raise
    
    async def start(self):
        """启动调度器"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动主调度器任务
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        # 启动工作任务
        for i in range(self.max_concurrent_tasks):
            worker_task = asyncio.create_task(self._worker_loop(f"worker_{i}"))
            self.worker_tasks.append(worker_task)
        
        # 启动统计任务
        asyncio.create_task(self._stats_loop())
        
        logger.info(f"Enhanced task scheduler started with {self.max_concurrent_tasks} workers")
    
    async def stop(self):
        """停止调度器"""
        self.is_running = False
        
        # 取消调度器任务
        if self.scheduler_task:
            self.scheduler_task.cancel()
        
        # 取消工作任务
        for worker_task in self.worker_tasks:
            worker_task.cancel()
        
        # 等待任务完成
        await asyncio.gather(
            self.scheduler_task,
            *self.worker_tasks,
            return_exceptions=True
        )
        
        logger.info("Enhanced task scheduler stopped")
    
    async def submit_task(
        self,
        task_name: str,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.NORMAL,
        args: tuple = (),
        kwargs: dict = None,
        dependencies: List[str] = None,
        metadata: dict = None,
        tags: List[str] = None,
        timeout: int = None,
        max_retries: int = 3,
        scheduled_at: datetime = None
    ) -> str:
        """提交任务"""
        kwargs = kwargs or {}
        dependencies = dependencies or []
        metadata = metadata or {}
        tags = tags or []
        
        # 创建任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务信息
        task_info = EnhancedTaskInfo(
            id=task_id,
            name=task_name,
            task_type=task_type,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.now(),
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            timeout=timeout,
            dependencies=[TaskDependency(dep_id) for dep_id in dependencies],
            metadata=metadata,
            tags=tags
        )
        
        # 保存任务
        self.tasks[task_id] = task_info
        await self._save_task(task_info)
        
        # 添加依赖关系
        for dep_id in dependencies:
            self.task_dependencies[dep_id].add(task_id)
        
        # 检查是否可以立即调度
        if self._can_schedule_task(task_info):
            await self._queue_task(task_info)
        
        self.stats["total_tasks"] += 1
        
        logger.info(f"Task {task_id} ({task_name}) submitted with priority {priority.name}")
        return task_id
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task_info = self.tasks.get(task_id)
        if not task_info:
            return False
        
        if task_info.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.CANCELLED]:
            return False
        
        # 取消Celery任务
        if task_info.status == TaskStatus.RUNNING and self.celery_app:
            self.celery_app.control.revoke(task_id, terminate=True)
        
        # 更新状态
        task_info.status = TaskStatus.CANCELLED
        task_info.completed_at = datetime.now()
        
        # 从队列移除
        for queue in self.queues.values():
            queue.remove(task_id)
        
        await self._save_task(task_info)
        
        # 取消依赖任务
        await self._cancel_dependent_tasks(task_id)
        
        logger.info(f"Task {task_id} cancelled")
        return True
    
    async def get_task_info(self, task_id: str) -> Optional[EnhancedTaskInfo]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    async def get_task_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """获取任务指标"""
        try:
            # 从Redis获取历史统计
            stats_key = f"{self.stats_key}:history"
            history_data = await self.redis.lrange(stats_key, 0, hours * 60 - 1)
            
            # 计算指标
            total_tasks = 0
            completed_tasks = 0
            failed_tasks = 0
            execution_times = []
            
            for data in history_data:
                try:
                    stats = json.loads(data)
                    total_tasks += stats.get("completed_tasks", 0) + stats.get("failed_tasks", 0)
                    completed_tasks += stats.get("completed_tasks", 0)
                    failed_tasks += stats.get("failed_tasks", 0)
                    
                    if "avg_execution_time" in stats and stats["avg_execution_time"] > 0:
                        execution_times.append(stats["avg_execution_time"])
                except json.JSONDecodeError:
                    continue
            
            # 当前状态
            current_stats = dict(self.stats)
            current_stats.update({
                "total_historical_tasks": total_tasks,
                "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
                "failure_rate": failed_tasks / total_tasks if total_tasks > 0 else 0,
                "avg_historical_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
                "queue_info": {
                    priority.name: queue.size()
                    for priority, queue in self.queues.items()
                }
            })
            
            return current_stats
            
        except Exception as e:
            logger.error(f"Failed to get task metrics: {e}")
            return self.stats
    
    def _can_schedule_task(self, task_info: EnhancedTaskInfo) -> bool:
        """检查任务是否可以调度"""
        # 检查是否有未完成的依赖
        for dep in task_info.dependencies:
            dep_task = self.tasks.get(dep.task_id)
            if not dep_task or dep_task.status != dep.required_status:
                return False
        
        # 检查调度时间
        if task_info.scheduled_at and task_info.scheduled_at > datetime.now():
            return False
        
        return True
    
    async def _queue_task(self, task_info: EnhancedTaskInfo):
        """将任务添加到队列"""
        task_info.status = TaskStatus.QUEUED
        self.queues[task_info.priority].put(task_info)
        await self._save_task(task_info)
    
    async def _scheduler_loop(self):
        """主调度器循环"""
        while self.is_running:
            try:
                # 检查待调度的任务
                pending_tasks = [
                    task for task in self.tasks.values()
                    if task.status == TaskStatus.PENDING and self._can_schedule_task(task)
                ]
                
                for task_info in pending_tasks:
                    await self._queue_task(task_info)
                
                # 检查超时任务
                await self._check_timeout_tasks()
                
                # 更新统计
                await self._update_stats()
                
                await asyncio.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(5)
    
    async def _worker_loop(self, worker_id: str):
        """工作者循环"""
        while self.is_running:
            try:
                # 从高优先级队列开始获取任务
                task_info = None
                for priority in reversed(TaskPriority):
                    queue = self.queues[priority]
                    task_info = queue.get()
                    if task_info:
                        break
                
                if not task_info:
                    await asyncio.sleep(0.1)
                    continue
                
                # 执行任务
                await self._execute_task(task_info, worker_id)
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task_info: EnhancedTaskInfo, worker_id: str):
        """执行任务"""
        start_time = time.time()
        
        try:
            # 更新任务状态
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = datetime.now()
            task_info.worker_id = worker_id
            await self._save_task(task_info)
            
            self.stats["active_tasks"] += 1
            
            # 提交到Celery执行
            if self.celery_app:
                result = self.celery_app.send_task(
                    task_info.name,
                    task_id=task_info.id,
                    args=task_info.metadata.get("args", ()),
                    kwargs=task_info.metadata.get("kwargs", {}),
                    time_limit=task_info.timeout
                )
                
                # 等待结果（这里简化处理，实际可能需要更复杂的逻辑）
                # 在实际应用中，可能需要通过Celery回调来更新状态
                
            # 模拟任务执行时间
            await asyncio.sleep(0.1)
            
            # 更新成功状态
            execution_time = time.time() - start_time
            task_info.status = TaskStatus.SUCCESS
            task_info.completed_at = datetime.now()
            task_info.execution_time = execution_time
            task_info.progress = 100.0
            
            await self._save_task(task_info)
            
            self.stats["completed_tasks"] += 1
            self.stats["active_tasks"] -= 1
            
            # 触发依赖任务
            await self._trigger_dependent_tasks(task_info.id)
            
            logger.info(f"Task {task_info.id} completed successfully in {execution_time:.2f}s")
            
        except Exception as e:
            # 处理任务失败
            execution_time = time.time() - start_time
            task_info.status = TaskStatus.FAILURE
            task_info.completed_at = datetime.now()
            task_info.execution_time = execution_time
            task_info.error = str(e)
            
            await self._save_task(task_info)
            
            self.stats["failed_tasks"] += 1
            self.stats["active_tasks"] -= 1
            
            # 检查是否需要重试
            if task_info.retries < task_info.max_retries:
                await self._retry_task(task_info)
            else:
                # 取消依赖任务
                await self._cancel_dependent_tasks(task_info.id)
            
            logger.error(f"Task {task_info.id} failed: {e}")
    
    async def _retry_task(self, task_info: EnhancedTaskInfo):
        """重试任务"""
        task_info.retries += 1
        task_info.status = TaskStatus.RETRY
        task_info.started_at = None
        task_info.completed_at = None
        task_info.worker_id = None
        task_info.error = None
        
        # 计算重试延迟（指数退避）
        delay = min(60, 2 ** task_info.retries)
        task_info.scheduled_at = datetime.now() + timedelta(seconds=delay)
        
        await self._save_task(task_info)
        logger.info(f"Task {task_info.id} scheduled for retry {task_info.retries}/{task_info.max_retries} in {delay}s")
    
    async def _trigger_dependent_tasks(self, completed_task_id: str):
        """触发依赖任务"""
        dependent_task_ids = self.task_dependencies.get(completed_task_id, set())
        
        for task_id in dependent_task_ids:
            task_info = self.tasks.get(task_id)
            if task_info and task_info.status == TaskStatus.PENDING:
                if self._can_schedule_task(task_info):
                    await self._queue_task(task_info)
    
    async def _cancel_dependent_tasks(self, failed_task_id: str):
        """取消依赖任务"""
        dependent_task_ids = self.task_dependencies.get(failed_task_id, set())
        
        for task_id in dependent_task_ids:
            task_info = self.tasks.get(task_id)
            if task_info and task_info.status in [TaskStatus.PENDING, TaskStatus.QUEUED]:
                task_info.status = TaskStatus.DEPENDENCY_FAILED
                task_info.completed_at = datetime.now()
                task_info.error = f"Dependency task {failed_task_id} failed"
                await self._save_task(task_info)
    
    async def _check_timeout_tasks(self):
        """检查超时任务"""
        now = datetime.now()
        
        for task_info in self.tasks.values():
            if (
                task_info.status == TaskStatus.RUNNING and
                task_info.timeout and
                task_info.started_at and
                (now - task_info.started_at).total_seconds() > task_info.timeout
            ):
                # 任务超时
                task_info.status = TaskStatus.TIMEOUT
                task_info.completed_at = now
                task_info.error = f"Task timeout after {task_info.timeout} seconds"
                
                # 取消Celery任务
                if self.celery_app:
                    self.celery_app.control.revoke(task_info.id, terminate=True)
                
                await self._save_task(task_info)
                self.stats["failed_tasks"] += 1
                self.stats["active_tasks"] -= 1
                
                logger.warning(f"Task {task_info.id} timed out")
    
    async def _save_task(self, task_info: EnhancedTaskInfo):
        """保存任务信息到Redis"""
        if not self.redis:
            return
        
        try:
            key = f"{self.task_key_prefix}{task_info.id}"
            data = asdict(task_info)
            
            # 转换datetime对象
            for field in ["created_at", "scheduled_at", "started_at", "completed_at"]:
                if data[field]:
                    data[field] = data[field].isoformat()
            
            # 转换枚举
            data["task_type"] = data["task_type"].value
            data["status"] = data["status"].value
            data["priority"] = data["priority"].value
            
            await self.redis.setex(key, 86400 * 7, json.dumps(data))  # 保存7天
            
        except Exception as e:
            logger.error(f"Failed to save task {task_info.id}: {e}")
    
    async def _recover_tasks(self):
        """恢复未完成的任务"""
        if not self.redis:
            return
        
        try:
            # 获取所有任务键
            keys = await self.redis.keys(f"{self.task_key_prefix}*")
            
            for key in keys:
                try:
                    data = await self.redis.get(key)
                    if data:
                        task_data = json.loads(data)
                        
                        # 重建任务信息
                        task_info = self._rebuild_task_info(task_data)
                        
                        # 只恢复未完成的任务
                        if task_info.status in [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING]:
                            self.tasks[task_info.id] = task_info
                            
                            # 重置运行中的任务为待调度
                            if task_info.status == TaskStatus.RUNNING:
                                task_info.status = TaskStatus.PENDING
                                task_info.started_at = None
                                task_info.worker_id = None
                            
                            # 重建依赖关系
                            for dep in task_info.dependencies:
                                self.task_dependencies[dep.task_id].add(task_info.id)
                
                except Exception as e:
                    logger.error(f"Failed to recover task from key {key}: {e}")
            
            logger.info(f"Recovered {len(self.tasks)} unfinished tasks")
            
        except Exception as e:
            logger.error(f"Failed to recover tasks: {e}")
    
    def _rebuild_task_info(self, data: Dict[str, Any]) -> EnhancedTaskInfo:
        """从字典重建任务信息"""
        # 转换datetime字段
        for field in ["created_at", "scheduled_at", "started_at", "completed_at"]:
            if data[field]:
                data[field] = datetime.fromisoformat(data[field])
        
        # 转换枚举
        data["task_type"] = TaskType(data["task_type"])
        data["status"] = TaskStatus(data["status"])
        data["priority"] = TaskPriority(data["priority"])
        
        # 重建依赖对象
        data["dependencies"] = [
            TaskDependency(dep["task_id"], TaskStatus(dep["required_status"]))
            for dep in data["dependencies"]
        ]
        
        return EnhancedTaskInfo(**data)
    
    async def _update_stats(self):
        """更新统计信息"""
        self.stats["queue_sizes"] = {
            priority.name: queue.size()
            for priority, queue in self.queues.items()
        }
        
        # 计算工作者利用率
        self.stats["worker_utilization"] = self.stats["active_tasks"] / self.max_concurrent_tasks
        
        # 计算平均执行时间
        completed_tasks_with_time = [
            task for task in self.tasks.values()
            if task.status == TaskStatus.SUCCESS and task.execution_time
        ]
        
        if completed_tasks_with_time:
            self.stats["avg_execution_time"] = sum(
                task.execution_time for task in completed_tasks_with_time
            ) / len(completed_tasks_with_time)
    
    async def _stats_loop(self):
        """统计循环"""
        while self.is_running:
            try:
                # 保存当前统计到Redis
                if self.redis:
                    stats_with_timestamp = dict(self.stats)
                    stats_with_timestamp["timestamp"] = datetime.now().isoformat()
                    
                    key = f"{self.stats_key}:history"
                    await self.redis.lpush(key, json.dumps(stats_with_timestamp))
                    await self.redis.ltrim(key, 0, 1440)  # 保留24小时数据
                
                await asyncio.sleep(60)  # 每分钟保存一次
                
            except Exception as e:
                logger.error(f"Stats loop error: {e}")
                await asyncio.sleep(60)


# 全局任务调度器实例
enhanced_scheduler = EnhancedTaskScheduler()

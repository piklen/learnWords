from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# 优化的数据库引擎配置
def create_optimized_engine(database_url: str, is_read_replica: bool = False):
    """创建优化的数据库引擎"""
    engine_config = {
        "poolclass": QueuePool,
        "pool_size": 20,  # 连接池大小
        "max_overflow": 30,  # 超出pool_size的最大连接数
        "pool_pre_ping": True,  # 连接前检查连接有效性
        "pool_recycle": 3600,  # 连接回收时间（1小时）
        "echo": settings.debug,  # 在调试模式下显示SQL
        "connect_args": {
            "sslmode": "prefer",
            "application_name": f"learnwords_{'read' if is_read_replica else 'write'}",
            "connect_timeout": 10,
            "options": "-c default_transaction_isolation=read committed"
        }
    }
    
    if is_read_replica:
        # 读副本优化
        engine_config["connect_args"]["options"] += " -c default_transaction_read_only=on"
    
    return create_engine(database_url, **engine_config)

# 主数据库引擎
engine = create_optimized_engine(settings.database_url)

# 读副本引擎（如果配置了的话）
read_replica_engine = None
if hasattr(settings, 'read_replica_database_url') and settings.read_replica_database_url:
    read_replica_engine = create_optimized_engine(settings.read_replica_database_url, is_read_replica=True)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ReadOnlySessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=read_replica_engine or engine
)

Base = declarative_base()

# 数据库事件监听器
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """设置PostgreSQL连接参数"""
    if hasattr(dbapi_connection, 'cursor'):
        cursor = dbapi_connection.cursor()
        # 设置连接参数
        cursor.execute("SET timezone TO 'UTC'")
        cursor.execute("SET statement_timeout = '30s'")
        cursor.execute("SET lock_timeout = '10s'")
        cursor.close()

@contextmanager
def get_db_transaction():
    """数据库事务上下文管理器"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_db():
    """获取数据库会话（写操作）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_read_db():
    """获取只读数据库会话（读操作）"""
    db = ReadOnlySessionLocal()
    try:
        yield db
    finally:
        db.close()

# 数据库健康检查
async def check_database_health():
    """检查数据库连接健康状态"""
    try:
        with get_db_transaction() as db:
            db.execute("SELECT 1")
            return {"status": "healthy", "type": "primary"}
    except Exception as e:
        logger.error(f"Primary database health check failed: {e}")
        return {"status": "unhealthy", "type": "primary", "error": str(e)}

async def check_read_replica_health():
    """检查读副本健康状态"""
    if not read_replica_engine:
        return {"status": "not_configured", "type": "read_replica"}
    
    try:
        db = ReadOnlySessionLocal()
        try:
            db.execute("SELECT 1")
            return {"status": "healthy", "type": "read_replica"}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Read replica health check failed: {e}")
        return {"status": "unhealthy", "type": "read_replica", "error": str(e)}

# 数据库迁移辅助函数
def run_migrations():
    """运行数据库迁移"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise

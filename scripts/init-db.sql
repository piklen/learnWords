-- 数据库初始化脚本
-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 设置时区
SET timezone = 'UTC';

-- 创建数据库用户（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'lesson_planner_user') THEN
        CREATE USER lesson_planner_user WITH PASSWORD 'lesson_planner_password';
    END IF;
END
$$;

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE lesson_planner TO lesson_planner_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lesson_planner_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO lesson_planner_user;

-- 设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lesson_planner_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lesson_planner_user;

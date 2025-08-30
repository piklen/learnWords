# 🚀 智能教案生成平台 - 生产环境部署指南

本文档详细介绍如何在生产环境中部署智能教案生成平台，包括服务器配置、第三方服务集成、安全设置等。

## 📋 目录
- [服务器要求](#服务器要求)
- [环境准备](#环境准备)
- [第三方服务配置](#第三方服务配置)
- [项目部署](#项目部署)
- [SSL证书配置](#ssl证书配置)
- [监控和日志](#监控和日志)
- [备份策略](#备份策略)
- [性能优化](#性能优化)
- [故障排除](#故障排除)

## 🖥️ 服务器要求

### 最低配置
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 40GB SSD
- **网络**: 10Mbps带宽
- **操作系统**: Ubuntu 20.04+ / CentOS 7+ / Debian 10+

### 推荐配置
- **CPU**: 4核心或以上
- **内存**: 8GB RAM或以上
- **存储**: 100GB SSD
- **网络**: 100Mbps带宽
- **操作系统**: Ubuntu 22.04 LTS

### 网络端口
需要开放以下端口：
- **22**: SSH管理
- **80**: HTTP访问
- **443**: HTTPS访问
- **6773**: 应用端口（可选，如果不使用反向代理）

## 🔧 环境准备

### 1. 更新系统
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 2. 安装必要软件
```bash
# Ubuntu/Debian
sudo apt install -y \
    docker.io \
    docker-compose \
    nginx \
    git \
    curl \
    wget \
    htop \
    ufw \
    certbot \
    python3-certbot-nginx

# CentOS/RHEL
sudo yum install -y \
    docker \
    docker-compose \
    nginx \
    git \
    curl \
    wget \
    htop \
    firewalld \
    certbot \
    python3-certbot-nginx
```

### 3. 启动Docker服务
```bash
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker
```

### 4. 配置防火墙
```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# CentOS/RHEL (Firewalld)
sudo systemctl start firewalld
sudo systemctl enable firewalld
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

## 🌐 第三方服务配置

### 1. Cloudflare R2存储配置

#### 步骤1: 创建R2存储桶
1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **R2 Object Storage**
3. 点击 **Create bucket**
4. 存储桶名称: `learnwords-prod-storage`
5. 选择合适的地区（建议选择距离服务器最近的）

#### 步骤2: 生成API令牌
1. 进入 **R2 Object Storage** → **Manage R2 API tokens**
2. 点击 **Create API token**
3. 配置如下：
   - **Token name**: `learnwords-production`
   - **Permissions**: Admin Read & Write
   - **Account resources**: Include - All accounts
   - **Zone resources**: Include - All zones
4. 保存生成的 **Access Key ID** 和 **Secret Access Key**

#### 步骤3: 配置公开访问（可选）
1. 在存储桶设置中配置自定义域名
2. 或使用R2的默认公开URL

### 2. Google Gemini API配置

#### 步骤1: 获取API密钥
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 使用Google账户登录
3. 点击 **Create API Key**
4. 选择或创建项目
5. 复制生成的API密钥

#### 步骤2: 设置配额和限制
1. 进入 [Google Cloud Console](https://console.cloud.google.com/)
2. 启用 **Generative AI API**
3. 配置适当的配额限制

### 3. 域名和DNS配置
```bash
# 配置DNS A记录
# 主域名: your-domain.com → 服务器IP
# API子域名: api.your-domain.com → 服务器IP (可选)
```

## 📦 项目部署

### 1. 创建部署目录
```bash
sudo mkdir -p /opt/learnwords
sudo chown $USER:$USER /opt/learnwords
cd /opt/learnwords
```

### 2. 克隆项目
```bash
git clone <your-repository-url> .
# 或者如果已有代码包
# tar -xzf learnwords.tar.gz
```

### 3. 配置环境变量
```bash
cp env.example .env.prod
```

编辑 `.env.prod` 文件：
```bash
nano .env.prod
```

**生产环境配置示例**：
```env
# 应用配置
APP_PORT=6773
DEBUG=false
SECRET_KEY=your-super-secure-secret-key-at-least-32-characters-long
HOST=0.0.0.0

# 数据库配置
POSTGRES_DB=lesson_planner_prod
POSTGRES_USER=learnwords_user
POSTGRES_PASSWORD=your-very-secure-database-password
POSTGRES_PORT=5432

# Redis配置
REDIS_PORT=6379

# Cloudflare R2存储配置
STORAGE_BACKEND=r2
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=learnwords-prod-storage
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ENDPOINT_URL=https://your_account_id.r2.cloudflarestorage.com
R2_PUBLIC_DOMAIN=files.your-domain.com

# AI服务配置
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash

# 安全配置
ALLOWED_HOSTS=your-domain.com,api.your-domain.com,localhost

# Worker配置
WORKER_CONCURRENCY=4

# Nginx配置
NGINX_PORT=80
NGINX_SSL_PORT=443

# 生产环境标识
NODE_ENV=production
```

### 4. 生成安全密钥
```bash
# 生成SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# 生成数据库密码
python3 -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(16))"
```

### 5. 创建必要目录
```bash
mkdir -p logs uploads backups ssl
sudo chown -R $USER:$USER logs uploads backups ssl
chmod 755 logs uploads backups
chmod 700 ssl
```

### 6. 配置Nginx

创建生产环境Nginx配置：
```bash
sudo nano /etc/nginx/sites-available/learnwords
```

**Nginx配置内容**：
```nginx
# /etc/nginx/sites-available/learnwords

upstream learnwords_app {
    server 127.0.0.1:6773;
    keepalive 32;
}

# HTTP服务器 - 重定向到HTTPS
server {
    listen 80;
    server_name your-domain.com api.your-domain.com;
    
    # Let's Encrypt验证
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # 重定向到HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS主服务器
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL配置
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    # 基本配置
    client_max_body_size 50M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    
    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml;

    # API请求
    location /api/ {
        proxy_pass http://learnwords_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket支持
    location /ws/ {
        proxy_pass http://learnwords_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # 健康检查
    location /health {
        proxy_pass http://learnwords_app;
        access_log off;
    }

    # 静态文件缓存
    location /static/ {
        alias /opt/learnwords/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
    }

    # 默认请求
    location / {
        proxy_pass http://learnwords_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 7. 启用Nginx站点
```bash
sudo ln -s /etc/nginx/sites-available/learnwords /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔒 SSL证书配置

### 1. 获取Let's Encrypt证书
```bash
# 停止nginx临时
sudo systemctl stop nginx

# 获取证书
sudo certbot certonly --standalone -d your-domain.com -d api.your-domain.com

# 启动nginx
sudo systemctl start nginx
```

### 2. 自动续期配置
```bash
# 测试自动续期
sudo certbot renew --dry-run

# 设置自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet --reload-hook "systemctl reload nginx"
```

## 🚀 启动应用

### 1. 构建和启动服务
```bash
cd /opt/learnwords

# 使用生产环境配置启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 查看服务状态
docker-compose ps
```

### 2. 初始化数据库
```bash
# 运行数据库迁移
docker-compose exec app alembic upgrade head

# 创建管理员用户（可选）
docker-compose exec app python scripts/create_admin.py
```

### 3. 验证部署
```bash
# 检查应用健康
curl -k https://your-domain.com/health

# 检查API文档
curl -k https://your-domain.com/api/docs

# 检查容器状态
docker-compose logs -f app
```

## 📊 监控和日志

### 1. 日志配置
```bash
# 创建日志轮转配置
sudo nano /etc/logrotate.d/learnwords
```

**日志轮转配置**：
```
/opt/learnwords/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker-compose -f /opt/learnwords/docker-compose.yml -f /opt/learnwords/docker-compose.prod.yml restart app worker
    endscript
}
```

### 2. 系统监控脚本
```bash
# 创建监控脚本
cat > /opt/learnwords/monitor.sh << 'EOF'
#!/bin/bash

# 系统监控脚本
DATE=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="/opt/learnwords/logs/monitor.log"

echo "[$DATE] 开始系统检查" >> $LOG_FILE

# 检查磁盘空间
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "[$DATE] 警告: 磁盘使用率 ${DISK_USAGE}%" >> $LOG_FILE
fi

# 检查内存使用
MEM_USAGE=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
if (( $(echo "$MEM_USAGE > 80" | bc -l) )); then
    echo "[$DATE] 警告: 内存使用率 ${MEM_USAGE}%" >> $LOG_FILE
fi

# 检查Docker容器状态
cd /opt/learnwords
UNHEALTHY_CONTAINERS=$(docker-compose ps | grep -v "Up" | grep -v "Name" | wc -l)
if [ $UNHEALTHY_CONTAINERS -gt 0 ]; then
    echo "[$DATE] 警告: $UNHEALTHY_CONTAINERS 个容器状态异常" >> $LOG_FILE
fi

# 检查应用健康
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6773/health)
if [ $HTTP_STATUS -ne 200 ]; then
    echo "[$DATE] 错误: 应用健康检查失败 (状态码: $HTTP_STATUS)" >> $LOG_FILE
fi

echo "[$DATE] 系统检查完成" >> $LOG_FILE
EOF

chmod +x /opt/learnwords/monitor.sh

# 设置定时监控
crontab -e
# 添加: */5 * * * * /opt/learnwords/monitor.sh
```

### 3. 性能监控
```bash
# 安装htop和iotop
sudo apt install htop iotop

# 查看实时性能
htop

# 查看Docker统计
docker stats

# 查看应用日志
docker-compose logs -f --tail=100 app
```

## 💾 备份策略

### 1. 自动备份脚本
```bash
cat > /opt/learnwords/backup.sh << 'EOF'
#!/bin/bash

# 备份配置
BACKUP_DIR="/opt/backups/learnwords"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 创建备份目录
mkdir -p $BACKUP_DIR

echo "开始备份 - $DATE"

# 备份数据库
echo "备份数据库..."
docker exec learnwords_postgres pg_dump -U learnwords_user lesson_planner_prod | gzip > $BACKUP_DIR/database_$DATE.sql.gz

# 备份应用配置
echo "备份配置文件..."
tar -czf $BACKUP_DIR/config_$DATE.tar.gz -C /opt/learnwords .env.prod docker-compose.yml docker-compose.prod.yml

# 备份上传文件（如果使用本地存储）
if [ -d "/opt/learnwords/uploads" ]; then
    echo "备份上传文件..."
    tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C /opt/learnwords uploads/
fi

# 备份日志文件
echo "备份日志文件..."
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz -C /opt/learnwords logs/

# 清理旧备份
echo "清理旧备份..."
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "备份完成 - $DATE"
EOF

chmod +x /opt/learnwords/backup.sh

# 设置每日备份
crontab -e
# 添加: 0 2 * * * /opt/learnwords/backup.sh >> /opt/learnwords/logs/backup.log 2>&1
```

### 2. 云端备份（可选）
```bash
# 安装rclone进行云端同步
curl https://rclone.org/install.sh | sudo bash

# 配置云存储
rclone config

# 同步备份到云端
rclone sync /opt/backups/learnwords remote:learnwords-backups
```

## ⚡ 性能优化

### 1. 数据库优化
```bash
# 编辑PostgreSQL配置
docker exec -it learnwords_postgres bash
# 在容器内编辑 /var/lib/postgresql/data/postgresql.conf

# 推荐配置项：
# shared_buffers = 256MB
# effective_cache_size = 1GB
# maintenance_work_mem = 64MB
# checkpoint_completion_target = 0.9
# wal_buffers = 16MB
# default_statistics_target = 100
```

### 2. Redis优化
```bash
# 编辑Redis配置
docker exec -it learnwords_redis redis-cli CONFIG SET maxmemory 512mb
docker exec -it learnwords_redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### 3. 应用优化
```bash
# 调整Worker数量
# 在 .env.prod 中设置：
WORKER_CONCURRENCY=4  # 根据CPU核心数调整

# 调整应用进程数
# 在 docker-compose.prod.yml 中设置：
# command: uvicorn app.main:app --host 0.0.0.0 --port 6773 --workers 4
```

### 4. 系统优化
```bash
# 优化系统参数
sudo nano /etc/sysctl.conf

# 添加以下配置：
# net.core.somaxconn = 1024
# net.core.netdev_max_backlog = 5000
# net.ipv4.tcp_max_syn_backlog = 1024
# vm.swappiness = 10

# 应用配置
sudo sysctl -p
```

## 🔄 更新部署

### 1. 滚动更新脚本
```bash
cat > /opt/learnwords/update.sh << 'EOF'
#!/bin/bash

echo "开始更新部署..."

# 备份当前版本
./backup.sh

# 拉取最新代码
git fetch origin
git checkout main
git pull origin main

# 停止服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod down

# 重新构建并启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 运行数据库迁移
docker-compose exec app alembic upgrade head

# 验证部署
sleep 10
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:6773/health)
if [ $HTTP_STATUS -eq 200 ]; then
    echo "更新成功！"
else
    echo "更新失败，请检查日志"
    docker-compose logs app
fi
EOF

chmod +x /opt/learnwords/update.sh
```

### 2. 蓝绿部署（高级）
```bash
# 创建蓝绿部署脚本
cat > /opt/learnwords/blue-green-deploy.sh << 'EOF'
#!/bin/bash

CURRENT_ENV=$(docker-compose ps | grep "learnwords_app" | wc -l)
if [ $CURRENT_ENV -gt 0 ]; then
    NEW_ENV="green"
    OLD_ENV="blue"
else
    NEW_ENV="blue"
    OLD_ENV="green"
fi

echo "部署到 $NEW_ENV 环境..."

# 在新环境中启动服务
docker-compose -f docker-compose.${NEW_ENV}.yml up -d --build

# 健康检查
sleep 30
if curl -f http://localhost:6774/health; then
    echo "新环境健康检查通过，切换流量..."
    
    # 更新nginx配置指向新环境
    sed -i "s/127.0.0.1:677[34]/127.0.0.1:6774/" /etc/nginx/sites-available/learnwords
    sudo nginx -s reload
    
    # 停止旧环境
    docker-compose -f docker-compose.${OLD_ENV}.yml down
    
    echo "部署完成！"
else
    echo "新环境健康检查失败，回滚..."
    docker-compose -f docker-compose.${NEW_ENV}.yml down
    exit 1
fi
EOF
```

## 🆘 故障排除

### 1. 常见问题诊断

#### 应用无法启动
```bash
# 检查容器状态
docker-compose ps

# 查看启动日志
docker-compose logs app

# 检查端口占用
sudo netstat -tlnp | grep :6773

# 检查磁盘空间
df -h

# 检查内存使用
free -h
```

#### 数据库连接失败
```bash
# 检查数据库容器
docker-compose logs postgres

# 测试数据库连接
docker-compose exec postgres psql -U learnwords_user -d lesson_planner_prod -c "SELECT 1;"

# 检查数据库配置
docker-compose exec app env | grep DATABASE_URL
```

#### AI服务不可用
```bash
# 测试AI服务
curl -X GET "http://localhost:6773/api/v1/ai/health"

# 检查API密钥
docker-compose exec app env | grep GEMINI_API_KEY

# 查看AI服务日志
docker-compose logs app | grep -i "gemini\|ai"
```

#### 存储服务问题
```bash
# 测试存储连接
docker-compose exec app python -c "
from app.services.storage_service import storage_service
import asyncio
print(asyncio.run(storage_service.file_exists('test')))
"

# 检查存储配置
docker-compose exec app env | grep R2_
```

### 2. 性能问题诊断
```bash
# 查看系统负载
top
htop

# 查看Docker资源使用
docker stats

# 查看网络连接
sudo netstat -an | grep :6773

# 分析慢查询
docker-compose exec postgres psql -U learnwords_user -d lesson_planner_prod -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;"
```

### 3. 紧急恢复程序
```bash
# 1. 停止所有服务
docker-compose down

# 2. 恢复数据库备份
gunzip -c /opt/backups/learnwords/database_YYYYMMDD_HHMMSS.sql.gz | \
docker exec -i learnwords_postgres psql -U learnwords_user -d lesson_planner_prod

# 3. 恢复配置文件
tar -xzf /opt/backups/learnwords/config_YYYYMMDD_HHMMSS.tar.gz -C /opt/learnwords/

# 4. 重新启动服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d
```

## 📞 支持和维护

### 1. 日常维护检查清单
- [ ] 检查服务器资源使用情况
- [ ] 查看应用日志是否有异常
- [ ] 验证备份是否正常执行
- [ ] 检查SSL证书是否即将过期
- [ ] 监控API响应时间
- [ ] 检查存储空间使用情况

### 2. 定期维护任务
- **每日**: 查看监控报告，检查备份状态
- **每周**: 更新系统包，清理日志文件
- **每月**: 检查性能指标，优化数据库
- **每季度**: 安全审计，更新依赖包

### 3. 应急联系信息
```bash
# 创建应急信息文件
cat > /opt/learnwords/EMERGENCY.md << 'EOF'
# 应急联系信息

## 服务器信息
- IP地址: YOUR_SERVER_IP
- SSH用户: YOUR_USERNAME
- 域名: your-domain.com

## 重要文件路径
- 应用目录: /opt/learnwords
- 配置文件: /opt/learnwords/.env.prod
- 备份目录: /opt/backups/learnwords
- 日志目录: /opt/learnwords/logs

## 常用命令
- 查看服务状态: docker-compose ps
- 重启应用: docker-compose restart app
- 查看日志: docker-compose logs -f app
- 紧急停止: docker-compose down

## 联系方式
- 系统管理员: admin@your-domain.com
- 技术支持: support@your-domain.com
EOF
```

---

## 📝 结语

本部署指南涵盖了生产环境部署的各个方面。请根据实际情况调整配置参数，并定期更新和维护系统。

如有问题，请查看故障排除章节或联系技术支持。

**部署完成后，请务必**：
1. 修改所有默认密码
2. 配置监控和告警
3. 测试备份恢复流程
4. 制定应急响应计划

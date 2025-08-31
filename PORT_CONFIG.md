# 端口配置说明

## 🔌 端口分配

为避免常见端口冲突，本项目使用了非标准端口号：

### 外部访问端口（宿主机）
- **18773** - 应用主端口（FastAPI服务）
- **18080** - Nginx HTTP端口
- **18443** - Nginx HTTPS端口
- **15432** - PostgreSQL数据库端口（仅开发环境）
- **16379** - Redis缓存端口（仅开发环境）

### 内部端口（Docker容器间）
- **6773** - 应用容器内部端口
- **5432** - PostgreSQL容器内部端口
- **6379** - Redis容器内部端口
- **80** - Nginx容器内部HTTP端口
- **443** - Nginx容器内部HTTPS端口

## 🚀 访问地址

### 开发环境
- **应用API**: http://localhost:18773/api/docs
- **健康检查**: http://localhost:18773/health
- **Nginx代理**: http://localhost:18080/
- **数据库**: localhost:15432
- **Redis**: localhost:16379

### 生产环境
- **应用API**: http://localhost:18773/api/docs
- **Nginx HTTP**: http://localhost:18080/
- **Nginx HTTPS**: https://localhost:18443/
- **数据库和Redis**: 仅内部访问（提高安全性）

## 🔒 防火墙配置

### Ubuntu/Debian (UFW)
```bash
sudo ufw allow 22/tcp        # SSH
sudo ufw allow 18080/tcp     # HTTP
sudo ufw allow 18443/tcp     # HTTPS
sudo ufw allow 18773/tcp     # 应用（可选）
```

### CentOS/RHEL (Firewalld)
```bash
sudo firewall-cmd --permanent --add-port=22/tcp
sudo firewall-cmd --permanent --add-port=18080/tcp
sudo firewall-cmd --permanent --add-port=18443/tcp
sudo firewall-cmd --permanent --add-port=18773/tcp
sudo firewall-cmd --reload
```

## 🛠️ 端口修改

如果需要修改端口，请更新以下文件：

### 1. 环境变量文件
```bash
# 在 .env 或 .env.prod 中修改
APP_PORT=18773
NGINX_PORT=18080
NGINX_SSL_PORT=18443
POSTGRES_PORT=15432
REDIS_PORT=16379
```

### 2. 应用配置
```python
# app/core/config.py
port: int = 18773
```

### 3. Docker Compose配置
检查 `docker-compose.yml` 和 `docker-compose.prod.yml` 中的端口映射

## 🔍 端口冲突检查

### 检查端口占用
```bash
# 检查特定端口
sudo netstat -tlnp | grep :18773
sudo lsof -i :18773

# 检查所有端口
sudo netstat -tlnp | grep -E ':(18773|18080|18443|15432|16379)'
```

### 寻找可用端口
```bash
# 查找可用端口范围
for port in {18770..18780}; do
  (echo >/dev/tcp/localhost/$port) &>/dev/null && echo "Port $port is open" || echo "Port $port is available"
done
```

## 📝 端口选择原则

1. **避免系统保留端口** (0-1023)
2. **避免常用服务端口**:
   - 3000 (Node.js)
   - 5000 (Flask)
   - 8000/8080 (HTTP测试)
   - 5432 (PostgreSQL)
   - 6379 (Redis)
   - 3306 (MySQL)

3. **选择高端口号** (10000+)
4. **保持端口号易于记忆**
5. **预留端口范围** 以便扩展

## ⚠️ 注意事项

1. **生产环境安全**:
   - 数据库和Redis端口不对外暴露
   - 只开放必要的HTTP/HTTPS端口
   - 使用防火墙限制访问

2. **开发环境便利**:
   - 数据库端口可暴露便于调试
   - 所有端口都可访问

3. **云服务部署**:
   - 检查云服务商的端口限制
   - 配置安全组规则
   - 考虑负载均衡器端口映射

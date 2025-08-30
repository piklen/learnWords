# 智能教案生成平台 🎓

基于人工智能的智能教案生成系统，帮助教育工作者快速创建高质量、可定制的教案。支持多种AI服务提供商和云存储解决方案。

## ✨ 项目特色

- 🤖 **多AI支持**: 支持Google Gemini、OpenAI GPT、Anthropic Claude等多种AI模型
- ☁️ **云存储**: 集成Cloudflare R2存储，高性能、低成本
- 📚 **多格式支持**: 支持PDF、图片等教材格式上传和处理
- 🎯 **个性化定制**: 根据年级、学科、教学模式等要求定制教案
- ⚡ **异步处理**: 高效的后台文档处理和教案生成
- 🔒 **安全可靠**: 完整的用户认证和文件安全机制
- 🌐 **WebSocket**: 实时进度更新和通知
- 📤 **多格式导出**: 支持多种教案导出格式
- 🔄 **灵活配置**: 支持多种存储后端和AI提供商切换

## 🏗️ 技术架构

### 核心技术栈
- **后端框架**: FastAPI + Python 3.11
- **数据库**: PostgreSQL + Redis
- **异步任务**: Celery + Redis
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx

### AI服务支持
- **Google Gemini**: 主推AI服务，性价比高
- **OpenAI GPT**: 可选，支持GPT-4等模型
- **Anthropic Claude**: 可选，支持Claude-3系列

### 存储方案
- **Cloudflare R2**: 主要存储方案，兼容S3 API
- **AWS S3**: 备用存储方案
- **本地存储**: 开发环境支持

## 🚀 快速开始

### 环境要求

- Docker 和 Docker Compose
- Python 3.11+ (仅开发环境)

### 1. 克隆项目

```bash
git clone <repository-url>
cd learnWords
```

### 2. 配置环境变量

复制环境变量示例文件并配置：

```bash
cp env.example .env
```

编辑 `.env` 文件，填入必要的配置信息：

```env
# 应用配置
APP_PORT=6773
DEBUG=false
SECRET_KEY=your_secret_key_here

# Cloudflare R2存储配置（推荐）
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=your_bucket_name
R2_ACCOUNT_ID=your_account_id
R2_ENDPOINT_URL=https://your_account_id.r2.cloudflarestorage.com
STORAGE_BACKEND=r2

# AI服务配置
AI_PROVIDER=gemini

# Google Gemini API配置（推荐）
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

### 4. 访问应用

- **API文档**: http://localhost:6773/api/docs
- **健康检查**: http://localhost:6773/health
- **前端界面**: http://localhost:6773/

## 🔧 配置指南

### AI服务配置

#### Google Gemini (推荐)

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 创建API密钥
3. 在 `.env` 文件中配置：

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash  # 或 gemini-1.5-pro
```

#### OpenAI (可选)

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
```

#### Anthropic Claude (可选)

```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 存储配置

#### Cloudflare R2 (推荐)

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 R2 Object Storage
3. 创建存储桶
4. 生成 API 令牌
5. 配置环境变量：

```env
STORAGE_BACKEND=r2
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=your_bucket_name
R2_ACCOUNT_ID=your_account_id
```

#### AWS S3 (备用)

```env
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET=your_s3_bucket
AWS_REGION=us-east-1
```

#### 本地存储 (开发)

```env
STORAGE_BACKEND=local
```

## 📖 API文档

### 认证相关
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录

### 文档管理
- `POST /api/v1/documents/upload-url` - 获取上传URL
- `POST /api/v1/documents/{id}/process` - 触发文档处理
- `GET /api/v1/documents/` - 获取文档列表
- `GET /api/v1/documents/{id}` - 获取文档详情

### 教案生成
- `POST /api/v1/lesson-plans/` - 创建教案生成任务
- `GET /api/v1/lesson-plans/` - 获取教案列表
- `GET /api/v1/lesson-plans/{id}` - 获取教案详情
- `POST /api/v1/lesson-plans/{id}/regenerate` - 重新生成教案

### AI服务管理
- `GET /api/v1/ai/providers` - 获取AI提供商信息
- `GET /api/v1/ai/providers/available` - 获取可用提供商列表
- `POST /api/v1/ai/providers/switch` - 切换AI提供商
- `POST /api/v1/ai/generate` - 直接调用AI生成文本
- `POST /api/v1/ai/analyze` - AI文档分析
- `GET /api/v1/ai/health` - AI服务健康检查

### 导出功能
- `GET /api/v1/export/formats` - 获取支持的导出格式
- `POST /api/v1/export/lesson-plan/{id}` - 导出教案

### WebSocket
- `WS /api/v1/ws/{user_id}` - 实时通知和进度更新

## 🛠️ 开发指南

### 本地开发环境

1. **安装依赖**：
```bash
pip install -r requirements.txt
```

2. **启动数据库服务**：
```bash
docker-compose up postgres redis -d
```

3. **运行数据库迁移**：
```bash
alembic upgrade head
```

4. **启动应用**：
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 6773
```

5. **启动Worker**：
```bash
celery -A app.celery_app worker --loglevel=info
```

### 项目结构

```
app/
├── api/                    # API端点
│   └── v1/               # API版本1
│       ├── api.py        # 路由汇总
│       └── endpoints/    # 具体端点
├── core/                  # 核心配置
│   ├── config.py         # 应用配置
│   ├── database.py       # 数据库配置
│   ├── security.py       # 安全配置
│   └── middleware.py     # 中间件
├── models/                # 数据模型
├── schemas/               # Pydantic模型
├── services/              # 业务逻辑服务
│   ├── ai_service.py     # AI服务管理
│   ├── storage_service.py # 存储服务
│   └── prompt_engine.py  # 提示词引擎
├── tasks/                 # 异步任务
└── main.py               # 应用入口
```

### 添加新的AI提供商

1. 在 `app/services/ai_service.py` 中创建新的Provider类
2. 继承 `AIProvider` 抽象基类
3. 实现必要的方法
4. 在 `AIService` 中注册新提供商

### 添加新的存储后端

1. 在 `app/services/storage_service.py` 中添加新的存储逻辑
2. 更新 `_initialize_client` 方法
3. 实现相应的上传、下载、删除方法

## 📊 监控和运维

### 健康检查端点

- **应用健康**: `GET /health`
- **详细健康检查**: `GET /api/v1/health/health`
- **AI服务健康**: `GET /api/v1/ai/health`

### 日志管理

日志文件位置：
- 应用日志: `./logs/app.log`
- Worker日志: `./logs/worker.log`
- Nginx日志: `./logs/nginx/`

### 性能优化

1. **数据库优化**：
   - 启用连接池
   - 添加适当索引
   - 定期清理旧数据

2. **缓存策略**：
   - Redis缓存常用查询
   - 静态文件CDN加速

3. **异步处理**：
   - 文档处理异步化
   - 教案生成后台处理

## 🚀 部署指南

### 生产环境部署

1. **环境准备**：
```bash
# 创建生产环境配置
cp env.example .env.prod
# 编辑生产环境配置
```

2. **使用生产配置启动**：
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

3. **SSL证书配置**：
   - 将SSL证书放在 `nginx/ssl/` 目录
   - 更新 `nginx/nginx.conf` 配置

4. **域名配置**：
   - 配置DNS解析
   - 更新Nginx配置

### 扩展部署

- **水平扩展**: 增加Worker实例数量
- **负载均衡**: 使用Nginx负载均衡多个应用实例
- **数据库**: 配置主从复制或读写分离

## 🔒 安全考虑

- **API密钥管理**: 使用环境变量存储敏感信息
- **文件上传**: 限制文件类型和大小
- **访问控制**: JWT令牌认证
- **HTTPS**: 生产环境强制使用HTTPS
- **防护措施**: 集成速率限制和CORS保护

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🆘 故障排除

### 常见问题

1. **AI服务不可用**：
   - 检查API密钥配置
   - 确认网络连接
   - 查看AI服务健康检查

2. **文件上传失败**：
   - 检查存储配置
   - 确认存储桶权限
   - 查看存储服务日志

3. **教案生成缓慢**：
   - 检查Worker状态
   - 增加Worker实例
   - 优化AI提示词

4. **数据库连接问题**：
   - 检查数据库服务状态
   - 确认连接字符串
   - 查看数据库日志

### 获取帮助

- 查看API文档: http://localhost:6773/api/docs
- 检查应用日志: `docker-compose logs -f app`
- 查看Worker日志: `docker-compose logs -f worker`

## 🔄 更新日志

### v1.0.0
- ✅ 支持多种AI服务提供商 (Gemini, OpenAI, Claude)
- ✅ 集成Cloudflare R2存储
- ✅ 端口更改为6773
- ✅ 完善的API文档和配置指南
- ✅ WebSocket实时通知
- ✅ 多格式导出功能
- ✅ 完整的Docker化部署方案

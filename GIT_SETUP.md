# Git配置说明

## 📁 文件结构优化

### 新增的Git配置文件

1. **`.gitignore`** - 完整的Git忽略配置
   - 环境变量和敏感配置文件
   - Python运行时文件
   - 日志和上传文件
   - 操作系统特定文件
   - 开发工具临时文件

2. **`.gitattributes`** - Git属性配置
   - 行结束符规范化
   - 文件类型声明
   - 语言检测配置
   - 导出忽略设置

3. **目录结构**
   - `logs/.gitkeep` - 保持日志目录
   - `uploads/.gitkeep` - 保持上传目录
   - `static/.gitkeep` - 保持静态文件目录

## 🔒 安全性改进

### 被忽略的敏感文件类型
- `.env*` - 所有环境变量文件
- `*.key`, `*.pem` - 密钥和证书文件
- `logs/` - 日志文件（可能包含敏感信息）
- `uploads/` - 用户上传文件
- `__pycache__/` - Python缓存文件

### 重要提醒
⚠️ **在提交代码前，请确保：**
1. 所有敏感信息都在环境变量中
2. 没有硬编码的API密钥或密码
3. 配置文件使用示例值

## 🛠️ 开发建议

### 环境变量管理
```bash
# 复制示例配置
cp env.example .env

# 编辑实际配置（不会被提交）
nano .env
```

### 日志文件处理
```bash
# 查看日志（目录会被保持，但文件内容被忽略）
tail -f logs/app.log
```

### 上传文件测试
```bash
# 测试文件会被忽略，不会提交到仓库
curl -X POST -F "file=@test.pdf" http://localhost:6773/api/v1/documents/upload
```

## 📋 最佳实践

1. **定期清理**：
   ```bash
   # 清理Git未跟踪文件
   git clean -fd
   
   # 清理忽略的文件
   git clean -fxd
   ```

2. **检查提交内容**：
   ```bash
   # 查看将要提交的更改
   git diff --staged
   
   # 检查敏感信息
   git log --oneline -p | grep -i "password\|key\|secret"
   ```

3. **分支管理**：
   ```bash
   # 创建功能分支
   git checkout -b feature/new-feature
   
   # 提交前检查
   git status
   git diff
   ```

## 🚨 紧急情况处理

### 如果意外提交了敏感信息

1. **立即从历史中移除**：
   ```bash
   # 移除文件并重写历史
   git filter-branch --force --index-filter \
   'git rm --cached --ignore-unmatch path/to/sensitive/file' \
   --prune-empty --tag-name-filter cat -- --all
   
   # 强制推送（危险操作）
   git push origin --force --all
   ```

2. **更新所有相关密钥**：
   - 立即更换泄露的API密钥
   - 更改数据库密码
   - 重新生成访问令牌

## 📝 提交规范

建议使用以下提交信息格式：

```
类型(范围): 简短描述

详细描述（可选）

相关问题: #123
```

**类型示例**：
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建或工具更改

#!/bin/bash

# 智能教案生成平台部署脚本
# 使用方法: ./deploy.sh [dev|prod]

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和Docker Compose
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 检查环境变量文件
check_env_file() {
    local env_file=$1
    
    if [ ! -f "$env_file" ]; then
        log_warning "环境变量文件 $env_file 不存在"
        if [ -f "env.example" ]; then
            log_info "从 env.example 复制配置文件..."
            cp env.example "$env_file"
            log_warning "请编辑 $env_file 文件，配置正确的环境变量"
            read -p "按回车键继续..."
        else
            log_error "env.example 文件不存在"
            exit 1
        fi
    fi
    
    # 检查关键环境变量
    log_info "检查关键环境变量..."
    
    source "$env_file"
    
    local missing_vars=()
    
    if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your_secret_key_here" ]; then
        missing_vars+=("SECRET_KEY")
    fi
    
    if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "your_secure_password_here" ]; then
        missing_vars+=("POSTGRES_PASSWORD")
    fi
    
    if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key" ]; then
        missing_vars+=("GEMINI_API_KEY")
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "以下环境变量需要配置："
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        log_error "请编辑 $env_file 文件并重新运行脚本"
        exit 1
    fi
    
    log_success "环境变量检查通过"
}

# 生成安全密钥
generate_secrets() {
    local env_file=$1
    
    log_info "生成安全密钥..."
    
    # 生成SECRET_KEY
    if ! grep -q "SECRET_KEY=" "$env_file" || grep -q "SECRET_KEY=your_secret_key_here" "$env_file"; then
        local secret_key=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$secret_key/" "$env_file"
        log_success "已生成 SECRET_KEY"
    fi
    
    # 生成数据库密码
    if ! grep -q "POSTGRES_PASSWORD=" "$env_file" || grep -q "POSTGRES_PASSWORD=your_secure_password_here" "$env_file"; then
        local db_password=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
        sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$db_password/" "$env_file"
        log_success "已生成 POSTGRES_PASSWORD"
    fi
    
    # 生成Redis密码（仅生产环境）
    if [ "$1" = "prod" ]; then
        if ! grep -q "REDIS_PASSWORD=" "$env_file" || grep -q "REDIS_PASSWORD=your_secure_redis_password" "$env_file"; then
            local redis_password=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
            sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$redis_password/" "$env_file"
            log_success "已生成 REDIS_PASSWORD"
        fi
    fi
}

# 部署开发环境
deploy_dev() {
    log_info "部署开发环境..."
    
    local env_file=".env"
    check_env_file "$env_file"
    generate_secrets "dev"
    
    log_info "启动开发环境服务..."
    docker-compose --env-file "$env_file" up -d --build
    
    log_success "开发环境部署完成！"
    echo
    log_info "访问地址："
    echo "  - 应用首页: http://localhost:6773"
    echo "  - API文档: http://localhost:6773/api/docs"
    echo "  - 健康检查: http://localhost:6773/health"
}

# 部署生产环境
deploy_prod() {
    log_info "部署生产环境..."
    
    local env_file=".env.prod"
    check_env_file "$env_file"
    generate_secrets "prod"
    
    log_info "启动生产环境服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file "$env_file" up -d --build
    
    log_success "生产环境部署完成！"
    echo
    log_info "访问地址："
    echo "  - 应用首页: http://localhost:6773"
    echo "  - API文档: http://localhost:6773/api/docs"
    echo "  - 健康检查: http://localhost:6773/health"
}

# 显示服务状态
show_status() {
    log_info "服务状态："
    docker-compose ps
    echo
    
    log_info "服务日志 (最后20行)："
    docker-compose logs --tail=20
}

# 清理服务
cleanup() {
    log_info "清理服务..."
    docker-compose down -v
    docker system prune -f
    log_success "清理完成"
}

# 主函数
main() {
    local command=${1:-dev}
    
    echo "==================================="
    echo "  智能教案生成平台部署脚本"
    echo "==================================="
    echo
    
    check_dependencies
    
    case $command in
        "dev")
            deploy_dev
            ;;
        "prod")
            deploy_prod
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "help")
            echo "使用方法: $0 [command]"
            echo
            echo "命令:"
            echo "  dev      - 部署开发环境 (默认)"
            echo "  prod     - 部署生产环境"
            echo "  status   - 显示服务状态"
            echo "  cleanup  - 清理所有服务和数据"
            echo "  help     - 显示帮助信息"
            ;;
        *)
            log_error "未知命令: $command"
            echo "使用 '$0 help' 查看帮助"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"

#!/bin/bash

# 服务管理脚本
# 用于管理learnWords项目的Docker服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目目录
PROJECT_DIR="/opt/learnwords"

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

# 检查项目目录
check_project_dir() {
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "项目目录不存在: $PROJECT_DIR"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    
    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml 文件不存在"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "learnWords 服务管理脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start     启动所有服务"
    echo "  stop      停止所有服务"
    echo "  restart   重启所有服务"
    echo "  status    显示服务状态"
    echo "  logs      显示服务日志"
    echo "  build     重新构建服务"
    echo "  update    更新代码并重启服务"
    echo "  backup    备份数据库和文件"
    echo "  restore   恢复数据库和文件"
    echo "  clean     清理未使用的Docker资源"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start"
    echo "  $0 logs app"
    echo "  $0 backup"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    docker-compose up -d
    log_success "服务启动完成"
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    docker-compose down
    log_success "服务停止完成"
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    docker-compose restart
    log_success "服务重启完成"
}

# 显示服务状态
show_status() {
    log_info "服务状态:"
    docker-compose ps
    
    echo ""
    log_info "资源使用情况:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 显示服务日志
show_logs() {
    local service=${1:-""}
    
    if [ -n "$service" ]; then
        log_info "显示 $service 服务日志:"
        docker-compose logs -f "$service"
    else
        log_info "显示所有服务日志:"
        docker-compose logs -f
    fi
}

# 重新构建服务
rebuild_services() {
    log_info "重新构建服务..."
    docker-compose build --no-cache
    log_success "服务构建完成"
}

# 更新代码并重启
update_services() {
    log_info "更新代码并重启服务..."
    
    # 停止服务
    docker-compose down
    
    # 拉取最新代码（如果使用git）
    if [ -d ".git" ]; then
        git pull origin main
    fi
    
    # 重新构建并启动
    docker-compose up -d --build
    
    log_success "服务更新完成"
}

# 备份数据
backup_data() {
    log_info "开始备份数据..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 备份数据库
    log_info "备份数据库..."
    docker-compose exec -T postgres pg_dump -U postgres lesson_planner > "$BACKUP_DIR/database.sql"
    
    # 备份上传文件
    log_info "备份上传文件..."
    tar -czf "$BACKUP_DIR/uploads.tar.gz" uploads/
    
    # 备份配置文件
    log_info "备份配置文件..."
    cp .env "$BACKUP_DIR/"
    cp docker-compose.yml "$BACKUP_DIR/"
    
    log_success "备份完成: $BACKUP_DIR"
}

# 恢复数据
restore_data() {
    local backup_dir=${1:-""}
    
    if [ -z "$backup_dir" ]; then
        log_error "请指定备份目录"
        echo "可用的备份目录:"
        ls -la backups/ 2>/dev/null || echo "没有找到备份目录"
        exit 1
    fi
    
    if [ ! -d "backups/$backup_dir" ]; then
        log_error "备份目录不存在: backups/$backup_dir"
        exit 1
    fi
    
    log_info "开始恢复数据: $backup_dir"
    
    # 停止服务
    docker-compose down
    
    # 恢复数据库
    log_info "恢复数据库..."
    docker-compose up -d postgres
    sleep 10
    docker-compose exec -T postgres psql -U postgres -d lesson_planner < "backups/$backup_dir/database.sql"
    
    # 恢复上传文件
    log_info "恢复上传文件..."
    rm -rf uploads/
    tar -xzf "backups/$backup_dir/uploads.tar.gz"
    
    # 恢复配置文件
    log_info "恢复配置文件..."
    cp "backups/$backup_dir/.env" .
    cp "backups/$backup_dir/docker-compose.yml" .
    
    # 启动服务
    docker-compose up -d
    
    log_success "数据恢复完成"
}

# 清理Docker资源
clean_docker() {
    log_info "清理Docker资源..."
    
    # 清理未使用的容器
    docker container prune -f
    
    # 清理未使用的镜像
    docker image prune -f
    
    # 清理未使用的网络
    docker network prune -f
    
    # 清理未使用的卷
    docker volume prune -f
    
    log_success "Docker资源清理完成"
}

# 主函数
main() {
    # 检查项目目录
    check_project_dir
    
    # 解析命令
    case "${1:-help}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        build)
            rebuild_services
            ;;
        update)
            update_services
            ;;
        backup)
            backup_data
            ;;
        restore)
            restore_data "$2"
            ;;
        clean)
            clean_docker
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"

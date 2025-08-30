#!/bin/bash

# 系统监控脚本
# 用于监控learnWords项目的系统资源和服务状态

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
}

# 显示系统信息
show_system_info() {
    log_info "系统信息:"
    echo "操作系统: $(lsb_release -d | cut -f2)"
    echo "内核版本: $(uname -r)"
    echo "架构: $(uname -m)"
    echo "主机名: $(hostname)"
    echo "当前时间: $(date)"
    echo ""
}

# 显示系统资源使用情况
show_system_resources() {
    log_info "系统资源使用情况:"
    
    # CPU使用率
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    echo "CPU使用率: ${cpu_usage}%"
    
    # 内存使用情况
    memory_info=$(free -h | grep Mem)
    total_mem=$(echo $memory_info | awk '{print $2}')
    used_mem=$(echo $memory_info | awk '{print $3}')
    free_mem=$(echo $memory_info | awk '{print $4}')
    echo "内存使用: $used_mem / $total_mem (可用: $free_mem)"
    
    # 磁盘使用情况
    disk_usage=$(df -h / | tail -1 | awk '{print $5}')
    echo "磁盘使用率: $disk_usage"
    
    echo ""
}

# 显示Docker服务状态
show_docker_status() {
    log_info "Docker服务状态:"
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        return
    fi
    
    # 检查Docker服务状态
    if systemctl is-active --quiet docker; then
        echo "Docker服务: 运行中"
    else
        echo "Docker服务: 已停止"
    fi
    
    # 显示容器状态
    if [ -f "docker-compose.yml" ]; then
        echo ""
        log_info "容器状态:"
        docker-compose ps
    fi
    
    echo ""
}

# 显示网络连接状态
show_network_status() {
    log_info "网络连接状态:"
    
    # 监听端口
    echo "监听端口:"
    netstat -tlnp | grep LISTEN | head -10
    
    echo ""
    
    # 网络接口
    echo "网络接口:"
    ip addr show | grep -E "^[0-9]+:|inet " | head -20
    
    echo ""
}

# 显示服务健康状态
check_service_health() {
    log_info "服务健康状态检查:"
    
    # 检查应用服务
    if curl -f http://localhost/health &> /dev/null; then
        echo "应用服务: 健康 ✓"
    else
        echo "应用服务: 不健康 ✗"
    fi
    
    # 检查数据库连接
    if docker-compose exec -T postgres pg_isready -U postgres &> /dev/null; then
        echo "PostgreSQL: 健康 ✓"
    else
        echo "PostgreSQL: 不健康 ✗"
    fi
    
    # 检查Redis连接
    if docker-compose exec -T redis redis-cli ping &> /dev/null; then
        echo "Redis: 健康 ✓"
    else
        echo "Redis: 不健康 ✗"
    fi
    
    echo ""
}

# 显示日志统计
show_log_stats() {
    log_info "日志统计:"
    
    if [ -d "logs" ]; then
        echo "应用日志文件:"
        ls -la logs/ | head -10
        
        echo ""
        echo "最近的错误日志:"
        find logs/ -name "*.log" -type f -exec grep -l "ERROR\|ERROR" {} \; | head -5 | while read logfile; do
            echo "文件: $logfile"
            tail -3 "$logfile" | grep -i error || echo "  无错误日志"
        done
    else
        echo "日志目录不存在"
    fi
    
    echo ""
}

# 显示性能指标
show_performance_metrics() {
    log_info "性能指标:"
    
    # 响应时间
    if command -v curl &> /dev/null; then
        response_time=$(curl -w "%{time_total}" -o /dev/null -s http://localhost/health)
        echo "健康检查响应时间: ${response_time}s"
    fi
    
    # 数据库连接数
    if docker-compose exec -T postgres pg_isready -U postgres &> /dev/null; then
        db_connections=$(docker-compose exec -T postgres psql -U postgres -d lesson_planner -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ')
        echo "数据库连接数: ${db_connections:-0}"
    fi
    
    # Redis内存使用
    if docker-compose exec -T redis redis-cli ping &> /dev/null; then
        redis_memory=$(docker-compose exec -T redis redis-cli info memory | grep "used_memory_human" | cut -d: -f2)
        echo "Redis内存使用: ${redis_memory:-N/A}"
    fi
    
    echo ""
}

# 显示告警信息
show_alerts() {
    log_info "系统告警:"
    
    alerts=0
    
    # CPU使用率告警
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        log_warning "CPU使用率过高: ${cpu_usage}%"
        alerts=$((alerts + 1))
    fi
    
    # 内存使用率告警
    memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$memory_usage" -gt 80 ]; then
        log_warning "内存使用率过高: ${memory_usage}%"
        alerts=$((alerts + 1))
    fi
    
    # 磁盘使用率告警
    disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 80 ]; then
        log_warning "磁盘使用率过高: ${disk_usage}%"
        alerts=$((alerts + 1))
    fi
    
    # 服务健康状态告警
    if ! curl -f http://localhost/health &> /dev/null; then
        log_error "应用服务不健康"
        alerts=$((alerts + 1))
    fi
    
    if [ $alerts -eq 0 ]; then
        log_success "系统运行正常，无告警"
    else
        log_warning "发现 $alerts 个告警"
    fi
    
    echo ""
}

# 生成监控报告
generate_report() {
    local report_file="monitor_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "生成监控报告: $report_file"
    
    {
        echo "learnWords 系统监控报告"
        echo "生成时间: $(date)"
        echo "=================================="
        echo ""
        
        # 系统信息
        echo "系统信息:"
        lsb_release -d
        uname -r
        hostname
        echo ""
        
        # 资源使用情况
        echo "资源使用情况:"
        top -bn1 | grep "Cpu(s)"
        free -h | grep Mem
        df -h /
        echo ""
        
        # 服务状态
        echo "服务状态:"
        docker-compose ps 2>/dev/null || echo "Docker Compose未运行"
        echo ""
        
        # 网络状态
        echo "网络状态:"
        netstat -tlnp | grep LISTEN | head -10
        echo ""
        
    } > "$report_file"
    
    log_success "监控报告已生成: $report_file"
}

# 显示帮助信息
show_help() {
    echo "learnWords 系统监控脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  system     显示系统信息"
    echo "  resources  显示资源使用情况"
    echo "  docker     显示Docker状态"
    echo "  network    显示网络状态"
    echo "  health     检查服务健康状态"
    echo "  logs       显示日志统计"
    echo "  performance 显示性能指标"
    echo "  alerts     显示告警信息"
    echo "  report     生成监控报告"
    echo "  all        显示所有信息"
    echo "  help       显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 all"
    echo "  $0 health"
    echo "  $0 report"
}

# 主函数
main() {
    # 检查项目目录
    check_project_dir
    
    # 解析命令
    case "${1:-help}" in
        system)
            show_system_info
            ;;
        resources)
            show_system_resources
            ;;
        docker)
            show_docker_status
            ;;
        network)
            show_network_status
            ;;
        health)
            check_service_health
            ;;
        logs)
            show_log_stats
            ;;
        performance)
            show_performance_metrics
            ;;
        alerts)
            show_alerts
            ;;
        report)
            generate_report
            ;;
        all)
            show_system_info
            show_system_resources
            show_docker_status
            show_network_status
            check_service_health
            show_log_stats
            show_performance_metrics
            show_alerts
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

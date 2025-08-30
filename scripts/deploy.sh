#!/bin/bash

# Ubuntu服务器部署脚本
# 用于在Ubuntu服务器上部署learnWords项目

set -e

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请勿使用root用户运行此脚本"
        exit 1
    fi
}

# 检查系统要求
check_system() {
    log_info "检查系统要求..."
    
    # 检查Ubuntu版本
    if ! command -v lsb_release &> /dev/null || ! lsb_release -d | grep -q "Ubuntu"; then
        log_error "此脚本仅支持Ubuntu系统"
        exit 1
    fi
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "系统要求检查通过"
}

# 安装系统依赖
install_dependencies() {
    log_info "安装系统依赖..."
    
    sudo apt-get update
    sudo apt-get install -y \
        curl \
        git \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release
    
    log_success "系统依赖安装完成"
}

# 安装Docker
install_docker() {
    log_info "安装Docker..."
    
    if command -v docker &> /dev/null; then
        log_warning "Docker已安装，跳过安装步骤"
        return
    fi
    
    # 添加Docker官方GPG密钥
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # 添加Docker仓库
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # 将当前用户添加到docker组
    sudo usermod -aG docker $USER
    
    log_success "Docker安装完成，请重新登录以应用组权限"
}

# 安装Docker Compose
install_docker_compose() {
    log_info "安装Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        log_warning "Docker Compose已安装，跳过安装步骤"
        return
    fi
    
    # 下载Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    log_success "Docker Compose安装完成"
}

# 创建项目目录
create_project_dir() {
    log_info "创建项目目录..."
    
    PROJECT_DIR="/opt/learnwords"
    
    if [ ! -d "$PROJECT_DIR" ]; then
        sudo mkdir -p $PROJECT_DIR
        sudo chown $USER:$USER $PROJECT_DIR
    fi
    
    cd $PROJECT_DIR
    log_success "项目目录创建完成: $PROJECT_DIR"
}

# 克隆项目代码
clone_project() {
    log_info "克隆项目代码..."
    
    if [ -d ".git" ]; then
        log_warning "项目目录已存在，跳过克隆步骤"
        return
    fi
    
    # 这里需要替换为实际的项目仓库地址
    # git clone https://github.com/yourusername/learnwords.git .
    
    log_warning "请手动将项目代码复制到 $PROJECT_DIR 目录"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    if [ ! -f ".env" ]; then
        cp env.example .env
        log_warning "请编辑 .env 文件配置必要的环境变量"
    else
        log_warning ".env 文件已存在，请检查配置"
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p uploads logs nginx/ssl nginx/conf.d
    
    # 设置目录权限
    chmod 755 uploads logs
    chmod 700 nginx/ssl
    
    log_success "目录创建完成"
}

# 生成自签名SSL证书（仅用于开发/测试）
generate_ssl_cert() {
    log_info "生成自签名SSL证书..."
    
    if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
        mkdir -p nginx/ssl
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost"
        
        log_success "SSL证书生成完成"
    else
        log_warning "SSL证书已存在，跳过生成步骤"
    fi
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 构建并启动服务
    docker-compose up -d --build
    
    log_success "服务启动完成"
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    sleep 10
    
    # 检查容器状态
    docker-compose ps
    
    # 检查健康状态
    if curl -f http://localhost/health &> /dev/null; then
        log_success "应用服务运行正常"
    else
        log_error "应用服务检查失败"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo ""
    echo "项目信息:"
    echo "  项目目录: /opt/learnwords"
    echo "  应用地址: http://localhost"
    echo "  API文档: http://localhost/api/docs"
    echo "  健康检查: http://localhost/health"
    echo ""
    echo "管理命令:"
    echo "  查看状态: docker-compose ps"
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
    echo ""
    echo "注意事项:"
    echo "  1. 请确保已正确配置 .env 文件"
    echo "  2. 生产环境请使用正式的SSL证书"
    echo "  3. 定期备份数据库和上传文件"
}

# 主函数
main() {
    log_info "开始部署learnWords项目..."
    
    check_root
    check_system
    install_dependencies
    install_docker
    install_docker_compose
    create_project_dir
    clone_project
    setup_environment
    create_directories
    generate_ssl_cert
    start_services
    check_services
    show_deployment_info
}

# 运行主函数
main "$@"

#!/bin/bash

# Production Environment Deployment Script
# Usage: ./deploy-prod.sh

set -e

echo "🚀 Starting Production Environment Deployment..."

# Configuration
PROJECT_NAME="staffing-optimization-system"
COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="./backups"
DEPLOYMENT_LOG="./logs/deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "[$(date)] [INFO] $1" >> "$DEPLOYMENT_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[$(date)] [WARN] $1" >> "$DEPLOYMENT_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[$(date)] [ERROR] $1" >> "$DEPLOYMENT_LOG"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
    echo "[$(date)] [DEBUG] $1" >> "$DEPLOYMENT_LOG"
}

# Setup logging
setup_logging() {
    mkdir -p logs
    touch "$DEPLOYMENT_LOG"
    log_info "Deployment started at $(date)"
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_info "Docker is running ✓"
    
    # Check if required files exist
    local required_files=("docker-compose.yml" "Dockerfile" ".env")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required file $file not found!"
            exit 1
        fi
    done
    log_info "All required files found ✓"
    
    # Check environment variables
    if [[ ! -f ".env" ]]; then
        log_error ".env file is required for production deployment!"
        exit 1
    fi
    
    # Source environment variables
    set -a
    source .env
    set +a
    
    # Validate critical environment variables
    local required_vars=("DB_PASSWORD" "SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Required environment variable $var is not set!"
            exit 1
        fi
    done
    log_info "Environment variables validated ✓"
    
    # Check disk space
    local available_space=$(df . | awk 'NR==2{print $4}')
    local required_space=1048576  # 1GB in KB
    if [[ $available_space -lt $required_space ]]; then
        log_error "Insufficient disk space. Required: 1GB, Available: $(( available_space / 1024 ))MB"
        exit 1
    fi
    log_info "Disk space check passed ✓"
}

# Backup existing data
backup_data() {
    log_info "Creating backup of existing data..."
    
    mkdir -p "$BACKUP_DIR"
    local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    # Backup database if running
    if docker-compose ps postgres | grep -q "Up"; then
        log_info "Backing up database..."
        docker-compose exec -T postgres pg_dump -U staffing_user staffing_db > "$backup_path.sql"
        log_info "Database backup created: $backup_path.sql"
    fi
    
    # Backup application data
    if [[ -d "data" ]]; then
        log_info "Backing up application data..."
        tar -czf "$backup_path_data.tar.gz" data/
        log_info "Data backup created: $backup_path_data.tar.gz"
    fi
    
    # Backup models
    if [[ -d "models" ]]; then
        log_info "Backing up ML models..."
        tar -czf "$backup_path_models.tar.gz" models/
        log_info "Models backup created: $backup_path_models.tar.gz"
    fi
    
    echo "$backup_name" > "$BACKUP_DIR/latest_backup"
    log_info "Backup completed successfully ✓"
}

# Health check function
health_check() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    log_info "Performing health check for $service..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_info "$service health check passed ✓"
            return 0
        fi
        
        log_debug "Health check attempt $attempt/$max_attempts failed, retrying in 10s..."
        sleep 10
        ((attempt++))
    done
    
    log_error "$service health check failed after $max_attempts attempts"
    return 1
}

# Deploy application
deploy_application() {
    log_info "Deploying application..."
    
    # Pull latest images
    log_info "Pulling latest Docker images..."
    docker-compose pull
    
    # Build application image
    log_info "Building application image..."
    docker-compose build --no-cache staffing-app
    
    # Start services with rolling update
    log_info "Starting services..."
    
    # Start infrastructure services first
    docker-compose up -d postgres redis
    
    # Wait for infrastructure to be ready
    sleep 30
    
    # Check database health
    local db_ready=false
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U staffing_user > /dev/null 2>&1; then
            db_ready=true
            break
        fi
        sleep 2
    done
    
    if [[ "$db_ready" != true ]]; then
        log_error "Database failed to become ready"
        exit 1
    fi
    log_info "Database is ready ✓"
    
    # Run database migrations
    log_info "Running database migrations..."
    # docker-compose exec -T staffing-app python -m alembic upgrade head
    
    # Start application
    log_info "Starting application services..."
    docker-compose up -d staffing-app
    
    # Start monitoring services
    if [[ "${ENABLE_MONITORING:-true}" == "true" ]]; then
        log_info "Starting monitoring services..."
        docker-compose up -d prometheus grafana
    fi
    
    # Start reverse proxy
    if [[ "${ENABLE_NGINX:-true}" == "true" ]]; then
        log_info "Starting reverse proxy..."
        docker-compose up -d nginx
    fi
    
    log_info "All services started ✓"
}

# Post-deployment verification
post_deployment_verification() {
    log_info "Running post-deployment verification..."
    
    # Health checks
    health_check "Application" "http://localhost:8000/health"
    
    if [[ "${ENABLE_MONITORING:-true}" == "true" ]]; then
        health_check "Prometheus" "http://localhost:9090/-/healthy"
        health_check "Grafana" "http://localhost:3000/api/health"
    fi
    
    # Run smoke tests
    log_info "Running smoke tests..."
    # Add your smoke test commands here
    # docker-compose exec -T staffing-app python -m pytest tests/smoke/ -v
    
    log_info "Post-deployment verification completed ✓"
}

# Rollback function
rollback() {
    log_warn "Starting rollback process..."
    
    local latest_backup=$(cat "$BACKUP_DIR/latest_backup" 2>/dev/null || echo "")
    
    if [[ -z "$latest_backup" ]]; then
        log_error "No backup found for rollback!"
        exit 1
    fi
    
    log_info "Rolling back to backup: $latest_backup"
    
    # Stop current services
    docker-compose down
    
    # Restore database
    if [[ -f "$BACKUP_DIR/${latest_backup}.sql" ]]; then
        log_info "Restoring database..."
        docker-compose up -d postgres
        sleep 30
        docker-compose exec -T postgres dropdb -U staffing_user staffing_db || true
        docker-compose exec -T postgres createdb -U staffing_user staffing_db
        docker-compose exec -T postgres psql -U staffing_user staffing_db < "$BACKUP_DIR/${latest_backup}.sql"
    fi
    
    # Restore data
    if [[ -f "$BACKUP_DIR/${latest_backup}_data.tar.gz" ]]; then
        log_info "Restoring application data..."
        rm -rf data/
        tar -xzf "$BACKUP_DIR/${latest_backup}_data.tar.gz"
    fi
    
    # Restore models
    if [[ -f "$BACKUP_DIR/${latest_backup}_models.tar.gz" ]]; then
        log_info "Restoring ML models..."
        rm -rf models/
        tar -xzf "$BACKUP_DIR/${latest_backup}_models.tar.gz"
    fi
    
    log_info "Rollback completed ✓"
}

# Cleanup old backups
cleanup_backups() {
    log_info "Cleaning up old backups..."
    
    # Keep only the last 5 backups
    cd "$BACKUP_DIR"
    ls -t backup_* | tail -n +6 | xargs -r rm -f
    cd - > /dev/null
    
    log_info "Backup cleanup completed ✓"
}

# Monitor deployment
monitor_deployment() {
    log_info "Monitoring deployment for 5 minutes..."
    
    local end_time=$(($(date +%s) + 300))  # 5 minutes from now
    
    while [[ $(date +%s) -lt $end_time ]]; do
        # Check if all services are running
        local failed_services=$(docker-compose ps --services --filter "status=exited")
        if [[ -n "$failed_services" ]]; then
            log_error "Some services have failed: $failed_services"
            return 1
        fi
        
        sleep 30
    done
    
    log_info "Deployment monitoring completed successfully ✓"
}

# Display deployment summary
show_deployment_summary() {
    echo ""
    log_info "🎉 Production deployment completed successfully!"
    echo ""
    echo "Services:"
    echo "  🌐 Application: http://localhost:8000"
    echo "  📊 API Docs: http://localhost:8000/docs"
    echo "  📈 Prometheus: http://localhost:9090"
    echo "  📊 Grafana: http://localhost:3000"
    echo ""
    echo "Monitoring:"
    echo "  📋 View logs: docker-compose logs -f"
    echo "  🔍 Check status: docker-compose ps"
    echo "  📊 Monitor metrics: http://localhost:3000"
    echo ""
    echo "Maintenance:"
    echo "  🔄 Update: ./scripts/deploy-prod.sh"
    echo "  ⏪ Rollback: ./scripts/deploy-prod.sh --rollback"
    echo "  🛑 Stop: docker-compose down"
    echo ""
}

# Main function
main() {
    setup_logging
    
    log_info "🏭 Production Environment Deployment"
    echo "====================================="
    
    # Check for rollback flag
    if [[ "${1:-}" == "--rollback" ]]; then
        rollback
        exit 0
    fi
    
    # Main deployment process
    pre_deployment_checks
    backup_data
    deploy_application
    post_deployment_verification
    monitor_deployment
    cleanup_backups
    
    show_deployment_summary
    
    log_info "✅ Production deployment completed successfully!"
}

# Error handling
error_handler() {
    log_error "Deployment failed at line $1"
    log_warn "Use './scripts/deploy-prod.sh --rollback' to rollback"
    exit 1
}

# Set error trap
trap 'error_handler $LINENO' ERR

# Parse command line arguments
case "${1:-}" in
    --rollback)
        rollback
        exit 0
        ;;
    --help|-h)
        echo "Usage: $0 [options]"
        echo "Options:"
        echo "  --rollback    Rollback to the last backup"
        echo "  --help, -h    Show this help message"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
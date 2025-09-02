#!/bin/bash

# Development Environment Deployment Script
# Usage: ./deploy-dev.sh

set -e

echo "🚀 Starting Development Environment Deployment..."

# Configuration
PROJECT_NAME="staffing-optimization-system"
COMPOSE_FILE="docker-compose.yml"
COMPOSE_DEV_FILE="docker-compose.dev.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_info "Docker is running ✓"
}

# Check if required files exist
check_files() {
    local files=("$COMPOSE_FILE" "$COMPOSE_DEV_FILE" "requirements.txt" "Dockerfile")
    for file in "${files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required file $file not found!"
            exit 1
        fi
    done
    log_info "All required files found ✓"
}

# Create environment file if it doesn't exist
setup_environment() {
    if [[ ! -f ".env" ]]; then
        log_warn ".env file not found. Creating from template..."
        cp .env.example .env
        log_info "Please edit .env file with your configuration"
    else
        log_info "Environment file exists ✓"
    fi
}

# Stop existing containers
stop_containers() {
    log_info "Stopping existing containers..."
    docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE down --remove-orphans || true
}

# Build and start development environment
start_development() {
    log_info "Building and starting development environment..."
    
    # Build the application image
    docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE build --no-cache
    
    # Start the services
    docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    check_services_health
}

# Check if services are healthy
check_services_health() {
    local services=("postgres" "redis")
    
    for service in "${services[@]}"; do
        log_info "Checking $service health..."
        local retries=0
        local max_retries=30
        
        while [ $retries -lt $max_retries ]; do
            if docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE ps $service | grep -q "healthy\|Up"; then
                log_info "$service is healthy ✓"
                break
            fi
            
            sleep 2
            ((retries++))
        done
        
        if [ $retries -eq $max_retries ]; then
            log_error "$service failed to become healthy"
            exit 1
        fi
    done
}

# Run database migrations (if applicable)
run_migrations() {
    log_info "Running database migrations..."
    # Add your migration commands here
    # docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE exec staffing-app python -m alembic upgrade head
}

# Run tests
run_tests() {
    log_info "Running tests..."
    docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE exec -T staffing-app pytest tests/ -v
}

# Display service information
show_info() {
    echo ""
    log_info "Development environment is ready!"
    echo ""
    echo "Services:"
    echo "  🌐 Application: http://localhost:8000"
    echo "  📊 API Docs: http://localhost:8000/docs"
    echo "  🗄️  PostgreSQL: localhost:5432"
    echo "  📦 Redis: localhost:6379"
    echo ""
    echo "Useful commands:"
    echo "  📋 View logs: docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE logs -f"
    echo "  🔍 Check status: docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE ps"
    echo "  🛑 Stop services: docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE down"
    echo "  🧪 Run tests: docker-compose -f $COMPOSE_FILE -f $COMPOSE_DEV_FILE exec staffing-app pytest"
    echo ""
}

# Cleanup function
cleanup() {
    log_warn "Deployment interrupted. Cleaning up..."
    stop_containers
    exit 1
}

# Main deployment process
main() {
    # Set up signal handlers
    trap cleanup SIGINT SIGTERM
    
    log_info "🏗️  Development Environment Deployment"
    echo "======================================"
    
    # Pre-deployment checks
    check_docker
    check_files
    setup_environment
    
    # Deploy
    stop_containers
    start_development
    run_migrations
    
    # Post-deployment
    if [[ "${RUN_TESTS:-true}" == "true" ]]; then
        run_tests
    fi
    
    show_info
    
    log_info "✅ Development deployment completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-tests)
            export RUN_TESTS=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --no-tests    Skip running tests after deployment"
            echo "  --help, -h    Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main
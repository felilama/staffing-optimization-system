#!/bin/bash

# Secrets Management Script for Staffing Optimization System
# This script helps manage secrets securely across different environments

set -e

# Configuration
SECRETS_DIR="./secrets"
ENVIRONMENT="${ENVIRONMENT:-development}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create secrets directory structure
setup_secrets_directory() {
    log_info "Setting up secrets directory structure..."
    
    mkdir -p "$SECRETS_DIR"/{development,staging,production}
    mkdir -p "$SECRETS_DIR"/common
    
    # Create .gitignore for secrets
    cat > "$SECRETS_DIR/.gitignore" << EOF
# Ignore all secret files
*.key
*.pem
*.p12
*.jks
*.env
secrets.*
passwords.*
tokens.*

# Allow example files
*.example
*.template
EOF
    
    log_info "Secrets directory structure created ✓"
}

# Generate random password
generate_password() {
    local length="${1:-32}"
    openssl rand -base64 "$length" | tr -d "=+/" | cut -c1-"$length"
}

# Generate secrets for environment
generate_secrets() {
    local env="${1:-development}"
    local secrets_file="$SECRETS_DIR/$env/secrets.env"
    
    log_info "Generating secrets for $env environment..."
    
    # Create secrets file
    cat > "$secrets_file" << EOF
# Generated secrets for $env environment
# Generated on: $(date)

# Database
DB_PASSWORD=$(generate_password 24)
DB_ROOT_PASSWORD=$(generate_password 32)

# Application
SECRET_KEY=$(generate_password 64)
JWT_SECRET=$(generate_password 48)

# Redis
REDIS_PASSWORD=$(generate_password 24)

# Monitoring
GRAFANA_PASSWORD=$(generate_password 16)
PROMETHEUS_PASSWORD=$(generate_password 16)

# API Keys (replace with actual values)
EXTERNAL_API_KEY=your-external-api-key-here
NOTIFICATION_API_KEY=your-notification-api-key-here

# SSL/TLS (if using HTTPS)
SSL_CERTIFICATE_PATH=/etc/ssl/certs/staffing-app.crt
SSL_PRIVATE_KEY_PATH=/etc/ssl/private/staffing-app.key
EOF

    # Set restrictive permissions
    chmod 600 "$secrets_file"
    
    log_info "Secrets generated for $env environment ✓"
    log_warn "Remember to update placeholder API keys with actual values!"
}

# Encrypt secrets file
encrypt_secrets() {
    local env="${1:-development}"
    local secrets_file="$SECRETS_DIR/$env/secrets.env"
    local encrypted_file="$secrets_file.gpg"
    
    if [[ ! -f "$secrets_file" ]]; then
        log_error "Secrets file not found: $secrets_file"
        exit 1
    fi
    
    log_info "Encrypting secrets for $env environment..."
    
    # Encrypt using GPG
    gpg --symmetric --cipher-algo AES256 --output "$encrypted_file" "$secrets_file"
    
    # Remove unencrypted file
    rm "$secrets_file"
    
    log_info "Secrets encrypted successfully ✓"
    log_warn "Unencrypted secrets file has been removed"
}

# Decrypt secrets file
decrypt_secrets() {
    local env="${1:-development}"
    local encrypted_file="$SECRETS_DIR/$env/secrets.env.gpg"
    local secrets_file="$SECRETS_DIR/$env/secrets.env"
    
    if [[ ! -f "$encrypted_file" ]]; then
        log_error "Encrypted secrets file not found: $encrypted_file"
        exit 1
    fi
    
    log_info "Decrypting secrets for $env environment..."
    
    # Decrypt using GPG
    gpg --decrypt --output "$secrets_file" "$encrypted_file"
    
    # Set restrictive permissions
    chmod 600 "$secrets_file"
    
    log_info "Secrets decrypted successfully ✓"
}

# Load secrets into environment
load_secrets() {
    local env="${1:-development}"
    local secrets_file="$SECRETS_DIR/$env/secrets.env"
    
    if [[ ! -f "$secrets_file" ]]; then
        log_error "Secrets file not found: $secrets_file"
        log_info "Run './scripts/manage-secrets.sh generate $env' to create secrets"
        exit 1
    fi
    
    log_info "Loading secrets for $env environment..."
    
    # Source the secrets file
    set -a
    source "$secrets_file"
    set +a
    
    log_info "Secrets loaded successfully ✓"
}

# Create Kubernetes secrets
create_k8s_secrets() {
    local env="${1:-development}"
    local secrets_file="$SECRETS_DIR/$env/secrets.env"
    local namespace="${2:-staffing-optimization}"
    
    if [[ ! -f "$secrets_file" ]]; then
        log_error "Secrets file not found: $secrets_file"
        exit 1
    fi
    
    log_info "Creating Kubernetes secrets for $env environment..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secret from env file
    kubectl create secret generic staffing-app-secrets \
        --from-env-file="$secrets_file" \
        --namespace="$namespace" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "Kubernetes secrets created successfully ✓"
}

# Backup secrets
backup_secrets() {
    local backup_dir="./backups/secrets"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    log_info "Backing up secrets..."
    
    mkdir -p "$backup_dir"
    
    # Create encrypted backup
    tar -czf - "$SECRETS_DIR" | gpg --symmetric --cipher-algo AES256 --output "$backup_dir/secrets_backup_$timestamp.tar.gz.gpg"
    
    log_info "Secrets backup created: $backup_dir/secrets_backup_$timestamp.tar.gz.gpg"
}

# Show usage
show_usage() {
    echo "Usage: $0 <command> [environment] [options]"
    echo ""
    echo "Commands:"
    echo "  setup                    - Set up secrets directory structure"
    echo "  generate <env>           - Generate secrets for environment"
    echo "  encrypt <env>            - Encrypt secrets file"
    echo "  decrypt <env>            - Decrypt secrets file"
    echo "  load <env>               - Load secrets into environment"
    echo "  k8s-create <env> [ns]    - Create Kubernetes secrets"
    echo "  backup                   - Backup all secrets"
    echo ""
    echo "Environments: development, staging, production"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 generate development"
    echo "  $0 encrypt production"
    echo "  $0 load staging"
    echo "  $0 k8s-create production staffing-prod"
}

# Main function
main() {
    local command="${1:-help}"
    local env="${2:-development}"
    
    case "$command" in
        "setup")
            setup_secrets_directory
            ;;
        "generate")
            generate_secrets "$env"
            ;;
        "encrypt")
            encrypt_secrets "$env"
            ;;
        "decrypt")
            decrypt_secrets "$env"
            ;;
        "load")
            load_secrets "$env"
            ;;
        "k8s-create")
            create_k8s_secrets "$env" "$3"
            ;;
        "backup")
            backup_secrets
            ;;
        "help"|*)
            show_usage
            ;;
    esac
}

# Run main function
main "$@"
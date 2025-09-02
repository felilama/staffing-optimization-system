# Staffing Optimization System - Deployment Guide

## 🚀 Overview

The Staffing Optimization System is a production-ready application that uses machine learning to forecast demand and optimize workforce allocation. This guide covers deployment across different environments.

## 📋 Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows with WSL2
- **Docker**: 20.10+ and Docker Compose 2.0+
- **Memory**: Minimum 4GB RAM (8GB+ recommended for production)
- **Storage**: 10GB+ available disk space
- **Network**: Internet access for pulling Docker images

### Required Tools
```bash
# Docker and Docker Compose
docker --version  # Should be 20.10+
docker-compose --version  # Should be 2.0+

# Optional but recommended
git --version
curl --version
```

## 🏗️ Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd staffing-optimization-system

# Copy environment template
cp .env.example .env

# Edit configuration (important!)
nano .env
```

### 2. Development Deployment
```bash
# Start development environment
./scripts/deploy-dev.sh

# Check status
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

### 3. Access the Application
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🌍 Environment-Specific Deployments

### Development Environment

**Purpose**: Local development and testing

```bash
# Deploy
./scripts/deploy-dev.sh

# Run tests
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec staffing-app pytest

# Stop
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

**Features**:
- ✅ Hot reload enabled
- ✅ Debug mode active
- ✅ Exposed database ports
- ✅ Development dependencies included

### Staging Environment

**Purpose**: Pre-production testing

```bash
# Set environment
export ENVIRONMENT=staging

# Deploy
./scripts/deploy-prod.sh

# Monitor
docker-compose logs -f
```

**Features**:
- ✅ Production-like configuration
- ✅ Monitoring enabled
- ✅ Security headers
- ✅ Rate limiting

### Production Environment

**Purpose**: Live production system

```bash
# IMPORTANT: Configure secrets first!
./scripts/manage-secrets.sh setup
./scripts/manage-secrets.sh generate production

# Edit .env with production values
nano .env

# Deploy
./scripts/deploy-prod.sh

# Monitor health
curl http://localhost:8000/health
```

**Features**:
- ✅ Security hardened
- ✅ Automated backups
- ✅ Health checks
- ✅ Monitoring and alerting
- ✅ SSL/TLS ready

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Deployment environment | `development` | ✅ |
| `DEBUG` | Debug mode | `false` | ❌ |
| `DB_PASSWORD` | Database password | - | ✅ |
| `SECRET_KEY` | Application secret | - | ✅ |
| `API_HOST` | API host | `0.0.0.0` | ❌ |
| `API_PORT` | API port | `8000` | ❌ |

### Business Configuration

Update these values in `.env` for your organization:

```bash
# Labor Costs
REGULAR_HOURLY_RATE=18.50
OVERTIME_MULTIPLIER=1.5
TEMP_WORKER_RATE=22.00

# Service Targets
TARGET_SERVICE_LEVEL=0.98
UNDERSTAFFING_PENALTY=150.0

# Operational Constraints
MIN_STAFF_PER_SHIFT=2
MAX_STAFF_PER_SHIFT=25
```

## 🔐 Security & Secrets Management

### Generate Secrets
```bash
# Setup secrets directory
./scripts/manage-secrets.sh setup

# Generate secrets for environment
./scripts/manage-secrets.sh generate production

# Encrypt secrets (recommended for production)
./scripts/manage-secrets.sh encrypt production
```

### Security Checklist
- [ ] Change default passwords
- [ ] Use strong secret keys
- [ ] Enable HTTPS in production
- [ ] Configure firewall rules
- [ ] Regular security updates
- [ ] Monitor access logs

## 📊 Monitoring & Observability

### Built-in Monitoring
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Application Metrics**: http://localhost:8000/metrics

### Key Metrics
- Request rate and response times
- Error rates and status codes
- Model accuracy and performance
- Resource utilization
- Business KPIs (cost savings, service levels)

### Alerts Configuration
```bash
# Check alerting rules
cat monitoring/prometheus.yml

# View Grafana dashboards
# Default login: admin/admin123 (change in production!)
```

## 🗄️ Database Management

### Backup
```bash
# Manual backup
docker-compose exec postgres pg_dump -U staffing_user staffing_db > backup.sql

# Automated backup (included in deployment script)
./scripts/deploy-prod.sh  # Creates automatic backup
```

### Restore
```bash
# Restore from backup
docker-compose exec -T postgres psql -U staffing_user staffing_db < backup.sql
```

### Migration
```bash
# Run database migrations (when implemented)
# docker-compose exec staffing-app python -m alembic upgrade head
```

## 🧪 Testing

### Automated Testing
```bash
# Run all tests
docker-compose exec staffing-app pytest

# Run specific test categories
docker-compose exec staffing-app pytest -m unit
docker-compose exec staffing-app pytest -m integration
docker-compose exec staffing-app pytest -m api

# Generate coverage report
docker-compose exec staffing-app pytest --cov=src --cov-report=html
```

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Generate forecast
curl -X POST "http://localhost:8000/api/v1/forecast" \\
  -H "Content-Type: application/json" \\
  -d '{
    "start_date": "2024-12-01",
    "end_date": "2024-12-07",
    "shifts": ["Morning", "Evening"],
    "order_types": ["E-commerce"]
  }'
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the port
lsof -i :8000

# Stop conflicting services
docker-compose down
```

#### 2. Database Connection Failed
```bash
# Check database status
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Reset database
docker-compose down
docker volume rm staffing-optimization-system_postgres_data
docker-compose up -d postgres
```

#### 3. Out of Memory
```bash
# Check memory usage
docker stats

# Reduce worker count in production
# Edit docker-compose.yml: reduce API_WORKERS
```

#### 4. SSL/HTTPS Issues
```bash
# Generate self-signed certificate for testing
openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes

# Update nginx configuration
# Uncomment SSL configuration in nginx/nginx.conf
```

### Log Analysis
```bash
# Application logs
docker-compose logs -f staffing-app

# Database logs
docker-compose logs -f postgres

# All services
docker-compose logs -f

# Filter by timestamp
docker-compose logs --since="2024-01-01T00:00:00" staffing-app
```

### Performance Tuning
```bash
# Monitor resource usage
docker stats

# Check application metrics
curl http://localhost:8000/metrics

# Database performance
docker-compose exec postgres psql -U staffing_user -d staffing_db -c "
  SELECT query, mean_time, calls 
  FROM pg_stat_statements 
  ORDER BY mean_time DESC 
  LIMIT 10;"
```

## 🔄 Maintenance

### Regular Tasks

#### Weekly
- [ ] Check application logs for errors
- [ ] Review monitoring dashboards
- [ ] Backup verification
- [ ] Security updates

#### Monthly
- [ ] Update dependencies
- [ ] Performance review
- [ ] Capacity planning
- [ ] Security audit

### Updates and Rollbacks
```bash
# Update to latest version
git pull origin main
./scripts/deploy-prod.sh

# Rollback if needed
./scripts/deploy-prod.sh --rollback
```

### Cleanup
```bash
# Remove old Docker images
docker image prune -f

# Remove old backups (keep last 5)
ls -t backups/ | tail -n +6 | xargs rm -f

# Clean up logs
docker-compose exec staffing-app find logs/ -name "*.log" -mtime +30 -delete
```

## 📞 Support

### Getting Help
1. Check logs: `docker-compose logs -f`
2. Verify configuration: `cat .env`
3. Check system resources: `docker stats`
4. Review this documentation

### Emergency Procedures
```bash
# Stop all services immediately
docker-compose down

# Emergency rollback
./scripts/deploy-prod.sh --rollback

# Check system health
curl http://localhost:8000/health
```

## 📚 Additional Resources

### API Documentation
- Interactive API docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

### Architecture
- See `docs/architecture.md` for system design
- See `docs/api.md` for API reference
- See `docs/deployment.md` for advanced deployment options

### Development
- Contributing guidelines: `CONTRIBUTING.md`
- Development setup: `docs/development.md`
- Testing guide: `docs/testing.md`

---

## 🎯 Quick Reference

### Essential Commands
```bash
# Development
./scripts/deploy-dev.sh
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Production
./scripts/deploy-prod.sh
docker-compose logs -f

# Health Check
curl http://localhost:8000/health

# Stop Services
docker-compose down

# Emergency Rollback
./scripts/deploy-prod.sh --rollback
```

### Service URLs
- **Application**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090

---

*For additional support or questions, please refer to the project documentation or contact the development team.*
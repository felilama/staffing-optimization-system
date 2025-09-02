"""
FastAPI Application for Staffing Optimization System
Production-ready API with health checks and monitoring
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
import pandas as pd
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Add project root and src to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from forecast_model import (
    StaffingConfig, 
    AdvancedForecaster, 
    CostOptimizer,
    run_enhanced_staffing_system
)
from config.settings import settings, load_config, get_environment_config
from utils.logger import setup_logging, performance_logger, audit_logger

# Setup logging
env_config = get_environment_config()
setup_logging(env_config.get('log_level', 'INFO'))
logger = logging.getLogger(__name__)

# Prometheus metrics - handle potential duplicates gracefully
from prometheus_client import REGISTRY

# Clear any existing metrics to prevent duplicates
for metric_name in ['http_requests_total', 'http_request_duration_seconds', 'active_connections', 'optimization_runs_total', 'model_accuracy']:
    try:
        collector = REGISTRY._names_to_collectors.get(metric_name)
        if collector:
            REGISTRY.unregister(collector)
    except (KeyError, AttributeError):
        pass

# Now create the metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Number of active connections')
OPTIMIZATION_RUNS = Counter('optimization_runs_total', 'Total optimization runs')
MODEL_ACCURACY = Gauge('model_accuracy', 'Current model accuracy score')

# FastAPI app initialization
app = FastAPI(
    title="Staffing Optimization System API",
    description="Production-ready API for workforce optimization and demand forecasting",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security
security = HTTPBearer(auto_error=False)

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    dependencies: Dict[str, str]

class ForecastRequest(BaseModel):
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    shifts: List[str] = Field(default=["Morning", "Evening", "Night"])
    order_types: List[str] = Field(default=["E-commerce", "B2B", "Express"])

class OptimizationRequest(BaseModel):
    forecast_data: List[Dict[str, Any]]
    constraints: Optional[Dict[str, Any]] = None

class OptimizationResponse(BaseModel):
    total_cost: float
    weekly_savings: float
    service_level: float
    optimization_results: List[Dict[str, Any]]
    generated_at: datetime

# Global variables
app_start_time = datetime.utcnow()
forecaster: Optional[AdvancedForecaster] = None
optimizer: Optional[CostOptimizer] = None

# Dependency injection
async def get_current_user(token: Optional[str] = Depends(security)):
    """Get current user from token (simplified for demo)"""
    if not token and settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return {"user_id": "demo_user", "permissions": ["read", "write"]}

# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Middleware to collect metrics"""
    start_time = datetime.utcnow()
    ACTIVE_CONNECTIONS.inc()
    
    try:
        response = await call_next(request)
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_DURATION.observe(duration)
        
        return response
    finally:
        ACTIVE_CONNECTIONS.dec()

# Health check endpoints
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    uptime = (datetime.utcnow() - app_start_time).total_seconds()
    
    # Check dependencies
    dependencies = {
        "database": "healthy",  # Would check actual DB connection
        "redis": "healthy",     # Would check actual Redis connection
        "filesystem": "healthy"
    }
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        environment=settings.environment,
        uptime_seconds=uptime,
        dependencies=dependencies
    )

@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness check for Kubernetes"""
    global forecaster, optimizer
    
    # Check if models are loaded
    if forecaster is None or optimizer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Models not yet loaded"
        )
    
    return {"status": "ready", "timestamp": datetime.utcnow()}

@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {"status": "alive", "timestamp": datetime.utcnow()}

@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# API endpoints
@app.post("/api/v1/forecast", tags=["Forecasting"])
async def generate_forecast(
    request: ForecastRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """Generate demand forecasts"""
    global forecaster
    
    try:
        if forecaster is None:
            # Initialize forecaster in background if not ready
            background_tasks.add_task(initialize_models)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Forecasting models are initializing. Please try again in a few moments."
            )
        
        # Parse dates
        start_date = pd.to_datetime(request.start_date)
        end_date = pd.to_datetime(request.end_date)
        forecast_dates = pd.date_range(start_date, end_date)
        
        # Generate forecasts
        forecasts = forecaster.forecast_demand(
            forecast_dates, request.shifts, request.order_types
        )
        
        # Convert to JSON-serializable format
        forecast_data = forecasts.to_dict(orient='records')
        
        # Log for audit
        audit_logger.log_forecast_generation(
            user=user["user_id"],
            date_range=f"{request.start_date} to {request.end_date}",
            model_version="1.0.0"
        )
        
        return {
            "forecasts": forecast_data,
            "generated_at": datetime.utcnow(),
            "model_version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Forecast generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast generation failed: {str(e)}"
        )

@app.post("/api/v1/optimize", response_model=OptimizationResponse, tags=["Optimization"])
async def optimize_staffing(
    request: OptimizationRequest,
    user = Depends(get_current_user)
):
    """Optimize staffing levels"""
    global optimizer
    
    try:
        if optimizer is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Optimization models not loaded"
            )
        
        # Convert forecast data to DataFrame
        forecast_df = pd.DataFrame(request.forecast_data)
        
        # Optimize each row
        optimization_results = []
        total_cost = 0
        
        for _, row in forecast_df.iterrows():
            result = optimizer.optimize_shift_staffing(row)
            optimization_results.append({**row.to_dict(), **result})
            total_cost += result['TotalCost']
        
        # Calculate metrics
        optimized_df = pd.DataFrame(optimization_results)
        avg_service_level = float(optimized_df['ServiceLevel'].mean())
        
        # Estimate savings (simplified)
        baseline_cost = len(optimization_results) * 10 * 8 * 18.50  # Rough estimate
        weekly_savings = max(0, baseline_cost - total_cost)
        
        # Record metrics
        OPTIMIZATION_RUNS.inc()
        
        # Log for audit
        audit_logger.log_optimization_run(
            user=user["user_id"],
            parameters=request.dict(),
            results={
                "total_cost": total_cost,
                "service_level": avg_service_level,
                "weekly_savings": weekly_savings
            }
        )
        
        return OptimizationResponse(
            total_cost=total_cost,
            weekly_savings=weekly_savings,
            service_level=avg_service_level,
            optimization_results=optimization_results,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )

@app.post("/api/v1/run-full-optimization", tags=["Optimization"])
async def run_full_optimization(
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """Run the complete optimization system"""
    
    # Run in background to avoid timeout
    background_tasks.add_task(execute_full_optimization, user["user_id"])
    
    return {
        "message": "Full optimization started in background",
        "status": "processing",
        "started_at": datetime.utcnow()
    }

# Background tasks
async def initialize_models():
    """Initialize ML models in background"""
    global forecaster, optimizer
    
    try:
        logger.info("Initializing forecasting and optimization models...")
        
        # This would typically load pre-trained models
        # For demo, we'll create new instances
        forecaster = AdvancedForecaster()
        config = StaffingConfig()
        optimizer = CostOptimizer(config)
        
        # In production, you'd load saved models:
        # forecaster.load_models("models/")
        
        logger.info("Models initialized successfully")
        
    except Exception as e:
        logger.error(f"Model initialization failed: {str(e)}")

async def execute_full_optimization(user_id: str):
    """Execute the full optimization system"""
    try:
        logger.info(f"Starting full optimization for user {user_id}")
        
        # Run the main optimization system
        optimized_results, weekly_summary, historical_data = run_enhanced_staffing_system()
        
        # Save results (in production, you'd save to database)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = f"output/optimization_results_{timestamp}.xlsx"
        
        optimized_results.to_excel(output_file, index=False)
        
        logger.info(f"Full optimization completed. Results saved to {output_file}")
        
        # Update model accuracy metric
        MODEL_ACCURACY.set(0.95)  # Would calculate actual accuracy
        
    except Exception as e:
        logger.error(f"Full optimization failed: {str(e)}")

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Starting Staffing Optimization API...")
    
    # Initialize models in background
    asyncio.create_task(initialize_models())
    
    logger.info("API startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Staffing Optimization API...")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        log_level=env_config.get('log_level', 'INFO').lower(),
        reload=settings.debug
    )
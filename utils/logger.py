"""
Logging configuration for Staffing Optimization System
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any
import structlog
import json
from datetime import datetime


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path = Path("logs"),
    json_logs: bool = False
) -> None:
    """Setup application logging configuration"""
    
    # Create logs directory
    log_dir.mkdir(exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "json" if json_logs else "standard",
                "stream": sys.stdout
            },
            "file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json" if json_logs else "standard",
                "filename": log_dir / "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "error_file": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json" if json_logs else "standard",
                "filename": log_dir / "error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["console", "error_file"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["file"],
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(config)


class PerformanceLogger:
    """Performance monitoring logger"""
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = structlog.get_logger(logger_name)
    
    def log_execution_time(self, operation: str, duration: float, **kwargs):
        """Log execution time for operations"""
        self.logger.info(
            "Operation completed",
            operation=operation,
            duration_seconds=duration,
            **kwargs
        )
    
    def log_model_metrics(self, model_name: str, metrics: Dict[str, Any]):
        """Log ML model performance metrics"""
        self.logger.info(
            "Model metrics",
            model=model_name,
            **metrics
        )
    
    def log_optimization_results(self, optimization_type: str, results: Dict[str, Any]):
        """Log optimization results"""
        self.logger.info(
            "Optimization completed",
            type=optimization_type,
            **results
        )


class AuditLogger:
    """Audit trail logger for business operations"""
    
    def __init__(self, log_dir: Path = Path("logs")):
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup audit logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # Create audit log handler
        audit_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "audit.log",
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        
        formatter = logging.Formatter(
            '%(asctime)s [AUDIT] %(message)s'
        )
        audit_handler.setFormatter(formatter)
        self.logger.addHandler(audit_handler)
    
    def log_forecast_generation(self, user: str, date_range: str, model_version: str):
        """Log forecast generation events"""
        self.logger.info(json.dumps({
            "event": "forecast_generated",
            "user": user,
            "date_range": date_range,
            "model_version": model_version,
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    def log_optimization_run(self, user: str, parameters: Dict[str, Any], results: Dict[str, Any]):
        """Log optimization run events"""
        self.logger.info(json.dumps({
            "event": "optimization_run",
            "user": user,
            "parameters": parameters,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    def log_configuration_change(self, user: str, setting: str, old_value: Any, new_value: Any):
        """Log configuration changes"""
        self.logger.info(json.dumps({
            "event": "configuration_change",
            "user": user,
            "setting": setting,
            "old_value": str(old_value),
            "new_value": str(new_value),
            "timestamp": datetime.utcnow().isoformat()
        }))


# Export logger instances
performance_logger = PerformanceLogger()
audit_logger = AuditLogger()
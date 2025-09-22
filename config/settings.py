"""
Configuration Management for Staffing Optimization System
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic_settings import BaseSettings
import yaml
import json


class StaffingSettings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Settings
    app_name: str = "Staffing Optimization System"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    
    # Database Settings (if using database)
    database_url: Optional[str] = None
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # ML Model Settings
    model_retrain_interval_days: int = 7
    forecast_horizon_days: int = 7
    min_training_data_points: int = 20
    
    # Business Logic Settings
    regular_hourly_rate: float = 18.50
    overtime_multiplier: float = 1.5
    temp_worker_rate: float = 22.00
    target_service_level: float = 0.98
    understaffing_penalty: float = 150.0
    
    # Operational Constraints
    min_staff_per_shift: int = 2
    max_staff_per_shift: int = 25
    break_coverage_factor: float = 0.2
    
    # File Paths
    data_directory: Path = Path("data")
    output_directory: Path = Path("output")
    models_directory: Path = Path("models")
    logs_directory: Path = Path("logs")
    
    # External Services
    redis_url: Optional[str] = None
    monitoring_enabled: bool = True
    metrics_port: int = 9090
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    allowed_hosts: list = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Allow extra fields from environment


def load_config(config_file: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from file and environment variables"""
    
    settings = StaffingSettings()
    config = settings.dict()
    
    # Load additional config from YAML file if provided
    if config_file and config_file.exists():
        with open(config_file, 'r') as f:
            file_config = yaml.safe_load(f)
            config.update(file_config)
    
    # Create directories if they don't exist
    for dir_key in ['data_directory', 'output_directory', 'models_directory', 'logs_directory']:
        Path(config[dir_key]).mkdir(parents=True, exist_ok=True)
    
    return config


def get_environment_config() -> Dict[str, Any]:
    """Get environment-specific configuration"""
    
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    configs = {
        "development": {
            "debug": True,
            "api_workers": 1,
            "database_pool_size": 2,
            "log_level": "DEBUG"
        },
        "staging": {
            "debug": False,
            "api_workers": 2,
            "database_pool_size": 5,
            "log_level": "INFO"
        },
        "production": {
            "debug": False,
            "api_workers": 4,
            "database_pool_size": 10,
            "log_level": "WARNING",
            "monitoring_enabled": True
        }
    }
    
    return configs.get(env, configs["development"])


# Export settings instance
settings = StaffingSettings()
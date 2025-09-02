"""
Test configuration and fixtures for Staffing Optimization System
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch

# Import application modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forecast_model import StaffingConfig, AdvancedForecaster, CostOptimizer
from config.settings import StaffingSettings


@pytest.fixture
def staffing_config():
    """Fixture for StaffingConfig instance"""
    return StaffingConfig()


@pytest.fixture
def test_settings():
    """Fixture for test settings"""
    return StaffingSettings(
        environment="test",
        debug=True,
        database_url="sqlite:///test.db",
        data_directory=Path("test_data"),
        output_directory=Path("test_output"),
        models_directory=Path("test_models"),
        logs_directory=Path("test_logs")
    )


@pytest.fixture
def sample_historical_data():
    """Fixture for sample historical data"""
    np.random.seed(42)
    
    dates = pd.date_range(start="2024-01-01", end="2024-01-31")
    shifts = ["Morning", "Evening", "Night"]
    order_types = ["E-commerce", "B2B", "Express"]
    
    rows = []
    for date in dates:
        for shift in shifts:
            for order_type in order_types:
                rows.append({
                    "Date": date,
                    "Shift": shift,
                    "OrderType": order_type,
                    "OrderVolume": np.random.randint(50, 200),
                    "StaffScheduled": np.random.randint(3, 15),
                    "TotalPicks": np.random.randint(100, 300),
                    "Productivity": np.random.normal(18, 2),
                    "CapacityUtilization": np.random.uniform(0.7, 1.0),
                    "OvertimeHours": np.random.uniform(0, 10),
                    "SeasonalFactor": 1.0,
                    "IsWeekend": date.weekday() >= 5,
                    "IsHolidayWeek": False,
                    "Staff_forklift_certified": np.random.randint(1, 5),
                    "Staff_hazmat_trained": np.random.randint(1, 3),
                    "Staff_team_leads": np.random.randint(1, 2),
                    "Staff_experienced": np.random.randint(3, 8)
                })
    
    return pd.DataFrame(rows)


@pytest.fixture
def sample_forecast_data():
    """Fixture for sample forecast data"""
    dates = pd.date_range(start="2024-02-01", end="2024-02-07")
    shifts = ["Morning", "Evening", "Night"]
    order_types = ["E-commerce", "B2B", "Express"]
    
    rows = []
    for date in dates:
        for shift in shifts:
            for order_type in order_types:
                forecast_volume = np.random.randint(50, 200)
                rows.append({
                    "Date": date,
                    "Shift": shift,
                    "OrderType": order_type,
                    "ForecastVolume": forecast_volume,
                    "LowerBound": int(forecast_volume * 0.85),
                    "UpperBound": int(forecast_volume * 1.15),
                    "Uncertainty": forecast_volume * 0.15
                })
    
    return pd.DataFrame(rows)


@pytest.fixture
def trained_forecaster(sample_historical_data):
    """Fixture for trained forecaster"""
    forecaster = AdvancedForecaster()
    forecaster.train_models(sample_historical_data)
    return forecaster


@pytest.fixture
def cost_optimizer(staffing_config):
    """Fixture for cost optimizer"""
    return CostOptimizer(staffing_config)


@pytest.fixture
def temp_directory():
    """Fixture for temporary directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_database():
    """Fixture for mocked database"""
    with patch('sqlalchemy.create_engine') as mock_engine:
        mock_conn = Mock()
        mock_engine.return_value.connect.return_value = mock_conn
        yield mock_conn


@pytest.fixture(scope="session")
def test_data_directory():
    """Session-scoped fixture for test data directory"""
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    yield test_dir
    # Cleanup after all tests
    if test_dir.exists():
        shutil.rmtree(test_dir)


class MockRedis:
    """Mock Redis client for testing"""
    
    def __init__(self):
        self.data = {}
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value, ex=None):
        self.data[key] = value
        return True
    
    def delete(self, key):
        return self.data.pop(key, None) is not None
    
    def exists(self, key):
        return key in self.data


@pytest.fixture
def mock_redis():
    """Fixture for mock Redis client"""
    return MockRedis()


# Custom test markers
pytestmark = [
    pytest.mark.filterwarnings("ignore:.*pandas.*:UserWarning"),
    pytest.mark.filterwarnings("ignore:.*sklearn.*:UserWarning")
]
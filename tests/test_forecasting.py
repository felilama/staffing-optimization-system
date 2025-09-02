"""
Unit tests for the forecasting components
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from forecast_model import (
    StaffingConfig, 
    AdvancedForecaster, 
    CostOptimizer,
    generate_enhanced_historical_data
)


class TestStaffingConfig:
    """Test StaffingConfig class"""
    
    def test_staffing_config_initialization(self, staffing_config):
        """Test StaffingConfig initialization"""
        assert staffing_config.REGULAR_RATE == 18.50
        assert staffing_config.OVERTIME_RATE == 27.75
        assert staffing_config.MIN_STAFF_PER_SHIFT == 2
        assert staffing_config.MAX_STAFF_PER_SHIFT == 25
        assert staffing_config.TARGET_SERVICE_LEVEL == 0.98
    
    def test_skill_requirements(self, staffing_config):
        """Test skill requirements configuration"""
        assert 'forklift_certified' in staffing_config.SKILL_REQUIREMENTS
        assert 'hazmat_trained' in staffing_config.SKILL_REQUIREMENTS
        assert 'team_leads' in staffing_config.SKILL_REQUIREMENTS
        assert 'experienced' in staffing_config.SKILL_REQUIREMENTS
    
    def test_absenteeism_rates(self, staffing_config):
        """Test absenteeism rates configuration"""
        assert len(staffing_config.ABSENTEEISM_RATES) == 7  # 7 days of week
        assert all(0 <= rate <= 1 for rate in staffing_config.ABSENTEEISM_RATES)


class TestDataGeneration:
    """Test data generation functions"""
    
    def test_generate_enhanced_historical_data(self):
        """Test historical data generation"""
        data = generate_enhanced_historical_data(
            start_date="2024-01-01", 
            end_date="2024-01-07"
        )
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert 'Date' in data.columns
        assert 'Shift' in data.columns
        assert 'OrderType' in data.columns
        assert 'OrderVolume' in data.columns
        
        # Check data types
        assert pd.api.types.is_datetime64_any_dtype(data['Date'])
        assert data['OrderVolume'].dtype in [np.int64, np.int32]
        assert data['StaffScheduled'].dtype in [np.int64, np.int32]
    
    def test_data_generation_date_range(self):
        """Test data generation respects date range"""
        start_date = "2024-01-01"
        end_date = "2024-01-03"
        data = generate_enhanced_historical_data(start_date, end_date)
        
        unique_dates = data['Date'].dt.date.unique()
        expected_dates = pd.date_range(start_date, end_date).date
        
        assert len(unique_dates) == len(expected_dates)
    
    def test_data_generation_shifts_and_types(self):
        """Test data generation includes all shifts and order types"""
        data = generate_enhanced_historical_data(
            start_date="2024-01-01", 
            end_date="2024-01-01"
        )
        
        expected_shifts = ["Morning", "Evening", "Night"]
        expected_order_types = ["E-commerce", "B2B", "Express"]
        
        assert set(data['Shift'].unique()) == set(expected_shifts)
        assert set(data['OrderType'].unique()) == set(expected_order_types)


class TestAdvancedForecaster:
    """Test AdvancedForecaster class"""
    
    def test_forecaster_initialization(self):
        """Test forecaster initialization"""
        forecaster = AdvancedForecaster()
        assert forecaster.models == {}
        assert forecaster.feature_importance == {}
    
    def test_prepare_features(self, sample_historical_data):
        """Test feature preparation"""
        forecaster = AdvancedForecaster()
        features_df = forecaster.prepare_features(sample_historical_data)
        
        expected_features = [
            'DayOfWeek', 'Week', 'Month', 'IsWeekend',
            'Volume_Lag7', 'Volume_MA7', 'SeasonalSin', 'SeasonalCos'
        ]
        
        for feature in expected_features:
            assert feature in features_df.columns
    
    def test_train_models(self, sample_historical_data):
        """Test model training"""
        forecaster = AdvancedForecaster()
        
        # Mock the print function to avoid output during tests
        with patch('builtins.print'):
            forecaster.train_models(sample_historical_data)
        
        assert len(forecaster.models) > 0
        assert len(forecaster.feature_importance) > 0
    
    def test_forecast_demand(self, trained_forecaster):
        """Test demand forecasting"""
        forecast_dates = pd.date_range(start="2024-02-01", end="2024-02-03")
        shifts = ["Morning", "Evening"]
        order_types = ["E-commerce", "B2B"]
        
        forecasts = trained_forecaster.forecast_demand(
            forecast_dates, shifts, order_types
        )
        
        assert isinstance(forecasts, pd.DataFrame)
        assert 'ForecastVolume' in forecasts.columns
        assert 'LowerBound' in forecasts.columns
        assert 'UpperBound' in forecasts.columns
        assert len(forecasts) == len(forecast_dates) * len(shifts) * len(order_types)


class TestCostOptimizer:
    """Test CostOptimizer class"""
    
    def test_optimizer_initialization(self, cost_optimizer):
        """Test optimizer initialization"""
        assert cost_optimizer.config is not None
        assert hasattr(cost_optimizer.config, 'REGULAR_RATE')
    
    def test_calculate_total_cost(self, cost_optimizer):
        """Test total cost calculation"""
        staff_count = 10
        forecast_volume = 150
        order_type = "E-commerce"
        date = datetime(2024, 2, 1)  # Thursday
        shift = "Morning"
        
        cost_metrics = cost_optimizer.calculate_total_cost(
            staff_count, forecast_volume, order_type, date, shift
        )
        
        assert 'total_cost' in cost_metrics
        assert 'regular_cost' in cost_metrics
        assert 'overtime_cost' in cost_metrics
        assert 'understaffing_cost' in cost_metrics
        assert 'service_level' in cost_metrics
        
        # Validate cost components are non-negative
        assert cost_metrics['total_cost'] >= 0
        assert cost_metrics['regular_cost'] >= 0
        assert cost_metrics['overtime_cost'] >= 0
        assert cost_metrics['understaffing_cost'] >= 0
        assert 0 <= cost_metrics['service_level'] <= 1
    
    def test_calculate_skills_penalty(self, cost_optimizer):
        """Test skills penalty calculation"""
        penalty = cost_optimizer.calculate_skills_penalty(10)
        assert penalty >= 0
    
    def test_optimize_shift_staffing(self, cost_optimizer, sample_forecast_data):
        """Test shift staffing optimization"""
        forecast_row = sample_forecast_data.iloc[0]
        
        optimization_result = cost_optimizer.optimize_shift_staffing(forecast_row)
        
        assert 'OptimalStaff' in optimization_result
        assert 'TotalCost' in optimization_result
        assert 'ServiceLevel' in optimization_result
        
        # Validate constraints
        config = cost_optimizer.config
        assert config.MIN_STAFF_PER_SHIFT <= optimization_result['OptimalStaff']
        assert optimization_result['OptimalStaff'] <= config.MAX_STAFF_PER_SHIFT
        assert 0 <= optimization_result['ServiceLevel'] <= 1


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.integration
    def test_end_to_end_optimization(self, sample_historical_data):
        """Test end-to-end optimization process"""
        # Train forecaster
        forecaster = AdvancedForecaster()
        with patch('builtins.print'):
            forecaster.train_models(sample_historical_data)
        
        # Generate forecasts
        forecast_dates = pd.date_range(start="2024-02-01", end="2024-02-02")
        shifts = ["Morning", "Evening"]
        order_types = ["E-commerce"]
        
        forecast_df = forecaster.forecast_demand(forecast_dates, shifts, order_types)
        
        # Optimize staffing
        config = StaffingConfig()
        optimizer = CostOptimizer(config)
        
        optimization_results = []
        for _, row in forecast_df.iterrows():
            result = optimizer.optimize_shift_staffing(row)
            optimization_results.append({**row.to_dict(), **result})
        
        optimized_df = pd.DataFrame(optimization_results)
        
        # Validate results
        assert len(optimized_df) > 0
        assert 'OptimalStaff' in optimized_df.columns
        assert 'TotalCost' in optimized_df.columns
        assert optimized_df['TotalCost'].sum() > 0
    
    @pytest.mark.slow
    def test_large_dataset_performance(self):
        """Test performance with larger dataset"""
        # Generate larger dataset
        large_data = generate_enhanced_historical_data(
            start_date="2024-01-01", 
            end_date="2024-03-31"
        )
        
        forecaster = AdvancedForecaster()
        
        # Time the training
        import time
        start_time = time.time()
        
        with patch('builtins.print'):
            forecaster.train_models(large_data)
        
        training_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 30 seconds)
        assert training_time < 30
        assert len(forecaster.models) > 0


if __name__ == "__main__":
    pytest.main([__file__])
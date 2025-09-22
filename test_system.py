#!/usr/bin/env python3
"""
Quick test script to verify the staffing optimization system works
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test all critical imports"""
    print("🔍 Testing imports...")

    try:
        from config.settings import load_config, settings
        print("✅ Config imports work")

        from utils.logger import setup_logging, audit_logger, performance_logger
        print("✅ Logger imports work")

        sys.path.insert(0, str(project_root / "src"))
        from forecast_model import StaffingConfig, AdvancedForecaster, CostOptimizer
        print("✅ Forecast model imports work")

        from api.main import app
        print("✅ API imports work")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic system functionality"""
    print("\n🧪 Testing basic functionality...")

    try:
        # Test configuration
        from config.settings import load_config
        config = load_config()
        print(f"✅ Configuration loaded: {config['app_name']}")

        # Test staffing config
        from forecast_model import StaffingConfig
        staffing_config = StaffingConfig()
        print(f"✅ Staffing config: Regular rate ${staffing_config.REGULAR_RATE}/hr")

        # Test data generation (small sample)
        from forecast_model import generate_enhanced_historical_data
        import pandas as pd

        # Generate just a week of data for testing
        test_data = generate_enhanced_historical_data("2024-01-01", "2024-01-07")
        print(f"✅ Data generation: {len(test_data)} records created")

        # Test forecaster initialization
        from forecast_model import AdvancedForecaster
        forecaster = AdvancedForecaster()
        print("✅ Forecaster initialized")

        # Test optimizer initialization
        from forecast_model import CostOptimizer
        optimizer = CostOptimizer(staffing_config)
        print("✅ Optimizer initialized")

        return True
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_directories():
    """Test required directories exist"""
    print("\n📁 Testing directories...")

    required_dirs = ['data', 'output', 'models', 'logs']
    all_exist = True

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"❌ {dir_name}/ directory missing")
            all_exist = False

    return all_exist

def main():
    """Run all tests"""
    print("🚀 STAFFING OPTIMIZATION SYSTEM - QUICK TEST")
    print("=" * 50)

    # Test imports
    imports_ok = test_imports()

    # Test directories
    dirs_ok = test_directories()

    # Test functionality
    functionality_ok = test_basic_functionality()

    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")
    print(f"Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"Directories: {'✅ PASS' if dirs_ok else '❌ FAIL'}")
    print(f"Functionality: {'✅ PASS' if functionality_ok else '❌ FAIL'}")

    if imports_ok and dirs_ok and functionality_ok:
        print("\n🎉 ALL TESTS PASSED! System is ready to run.")
        print("\nTo run the system:")
        print("  1. Standalone: python src/main.py")
        print("  2. API Server: python api/main.py")
        print("  3. Docker: docker-compose up")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED! Check errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
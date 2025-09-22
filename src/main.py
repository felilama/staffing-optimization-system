#!/usr/bin/env python3
"""
Staffing Optimization System - Main Application Entry Point
Production-ready deployment version
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))

from forecast_model import run_enhanced_staffing_system, create_optimization_visualizations
from config.settings import load_config
from utils.logger import setup_logging

def main():
    """Main application entry point"""
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config()
        logger.info("Starting Staffing Optimization System...")
        
        # Run the optimization system
        optimized_results, weekly_summary, historical_data = run_enhanced_staffing_system()
        
        # Create visualizations if requested
        if config.get('generate_visualizations', True):
            create_optimization_visualizations(optimized_results, historical_data)
        
        logger.info("Optimization system completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Application failed: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
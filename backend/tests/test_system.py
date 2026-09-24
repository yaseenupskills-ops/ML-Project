"""
Test Script for Fall Detection System
-------------------------------------
Simple test to verify that core components can be imported and instantiated.
"""

import sys
import os
import logging

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        import pose_extraction
        print("✓ pose_extraction imported")
    except Exception as e:
        print(f"✗ pose_extraction import failed: {e}")
        return False
    
    try:
        import features
        print("✓ features imported")
    except Exception as e:
        print(f"✗ features import failed: {e}")
        return False
    
    try:
        import model_rf
        print("✓ model_rf imported")
    except Exception as e:
        print(f"✗ model_rf import failed: {e}")
        return False
    
    try:
        import decision_logic
        print("✓ decision_logic imported")
    except Exception as e:
        print(f"✗ decision_logic import failed: {e}")
        return False
    
    try:
        import grace_period
        print("✓ grace_period imported")
    except Exception as e:
        print(f"✗ grace_period import failed: {e}")
        return False
    
    try:
        import alert
        print("✓ alert imported")
    except Exception as e:
        print(f"✗ alert import failed: {e}")
        return False
    
    try:
        import simulate_stream
        print("✓ simulate_stream imported")
    except Exception as e:
        print(f"✗ simulate_stream import failed: {e}")
        return False
    
    try:
        import evaluate
        print("✓ evaluate imported")
    except Exception as e:
        print(f"✗ evaluate import failed: {e}")
        return False
    
    try:
        import model_cnn_lstm
        print("✓ model_cnn_lstm imported (stretch goal)")
    except Exception as e:
        print(f"⚠ model_cnn_lstm import failed: {e}")
        # This is OK as it's a stretch goal
    
    return True

def test_config_loading():
    """Test that configuration can be loaded."""
    print("\nTesting configuration loading...")
    
    try:
        import yaml
        from pathlib import Path
        
        config_path = "config.yaml.example"
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            print("✓ Configuration loaded successfully")
            print(f"  Pose config keys: {list(config.get('pose', {}).keys())}")
            print(f"  Features config keys: {list(config.get('features', {}).keys())}")
            return True
        else:
            print(f"✗ Config file {config_path} not found")
            return False
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of core components."""
    print("\nTesting basic functionality...")
    
    try:
        # Test pose extractor instantiation
        from pose_extraction import PoseExtractor
        extractor = PoseExtractor()
        print("✓ PoseExtractor instantiated")
        
        # Test feature engineer instantiation
        from features import FeatureEngineer
        engineer = FeatureEngineer()
        print("✓ FeatureEngineer instantiated")
        
        # Test decision logic instantiation
        from decision_logic import DecisionLogic
        dec_logic = DecisionLogic()
        print("✓ DecisionLogic instantiated")
        
        # Test grace period instantiation
        from grace_period import GracePeriodManager
        grace_manager = GracePeriodManager()
        print("✓ GracePeriodManager instantiated")
        
        # Test alert manager instantiation
        from alert import AlertManager
        alert_manager = AlertManager()
        print("✓ AlertManager instantiated")
        
        return True
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Fall Detection System - Component Test")
    print("=" * 40)
    
    # Set up logging
    logging.basicConfig(level=logging.WARNING)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
    
    # Test configuration
    if not test_config_loading():
        all_passed = False
    
    # Test basic functionality
    if not test_basic_functionality():
        all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All tests passed!")
        print("The core components are working correctly.")
        return 0
    else:
        print("✗ Some tests failed!")
        print("Please check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
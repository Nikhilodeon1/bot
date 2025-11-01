#!/usr/bin/env python3
"""
System Validation Script for Botted Library v2

Performs comprehensive validation of the integrated system to ensure
all components work together correctly.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from botted_library.core.system_integration import SystemIntegration, SystemConfiguration
from botted_library.core.system_startup import SystemStartup, StartupOptions
from botted_library.core.configuration_manager import ConfigurationManager
from botted_library.core.interfaces import WorkerType
from botted_library.compatibility.v1_compatibility import create_worker


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)


def print_success(message: str):
    """Print success message"""
    print(f"✅ {message}")


def print_error(message: str):
    """Print error message"""
    print(f"❌ {message}")


def print_info(message: str):
    """Print info message"""
    print(f"ℹ️  {message}")


def validate_imports():
    """Validate that all required modules can be imported"""
    print_header("Import Validation")
    
    try:
        # Core system components
        from botted_library.core.system_integration import SystemIntegration
        from botted_library.core.system_startup import SystemStartup
        from botted_library.core.configuration_manager import ConfigurationManager
        from botted_library.core.interfaces import WorkerType
        
        # Collaborative components
        from botted_library.core.collaborative_server import CollaborativeServer
        from botted_library.core.enhanced_worker_registry import EnhancedWorkerRegistry
        from botted_library.core.enhanced_worker import EnhancedWorker
        from botted_library.core.planner_worker import PlannerWorker
        from botted_library.core.executor_worker import ExecutorWorker
        from botted_library.core.verifier_worker import VerifierWorker
        
        # Mode controllers
        from botted_library.core.mode_manager import ModeManager
        from botted_library.core.manual_mode_controller import ManualModeController
        from botted_library.core.auto_mode_controller import AutoModeController
        
        # Collaborative spaces
        from botted_library.core.collaborative_space import CollaborativeSpace
        from botted_library.core.shared_whiteboard import SharedWhiteboard
        from botted_library.core.shared_filesystem import SharedFileSystem
        
        # Plugin and tools
        from botted_library.core.plugin_system import PluginManager
        from botted_library.core.enhanced_tools import EnhancedToolManager
        
        # Error handling and monitoring
        from botted_library.core.error_recovery import ErrorRecoverySystem
        from botted_library.core.monitoring_system import MonitoringSystem
        
        # Compatibility
        from botted_library.compatibility.v1_compatibility import create_worker
        
        print_success("All core modules imported successfully")
        return True
        
    except ImportError as e:
        print_error(f"Import failed: {e}")
        traceback.print_exc()
        return False


def validate_configuration():
    """Validate configuration management"""
    print_header("Configuration Validation")
    
    try:
        # Test configuration manager creation
        config_manager = ConfigurationManager()
        print_success("Configuration manager created")
        
        # Test configuration access
        config = config_manager.get_config()
        assert config is not None
        print_success("Configuration retrieved")
        
        # Test configuration modification
        original_host = config_manager.get_value("server_host")
        config_manager.set_value("server_host", "test-host")
        new_host = config_manager.get_value("server_host")
        assert new_host == "test-host"
        print_success("Configuration modification works")
        
        # Restore original value
        config_manager.set_value("server_host", original_host)
        
        # Test nested configuration
        config_manager.set_value("max_workers_per_type.PLANNER", 5)
        planner_count = config_manager.get_value("max_workers_per_type.PLANNER")
        assert planner_count == 5
        print_success("Nested configuration access works")
        
        return True
        
    except Exception as e:
        print_error(f"Configuration validation failed: {e}")
        traceback.print_exc()
        return False


def validate_worker_types():
    """Validate worker type enumeration"""
    print_header("Worker Type Validation")
    
    try:
        # Test WorkerType enum
        assert WorkerType.PLANNER.value == "planner"
        assert WorkerType.EXECUTOR.value == "executor"
        assert WorkerType.VERIFIER.value == "verifier"
        print_success("WorkerType enum values correct")
        
        # Test enum iteration
        worker_types = list(WorkerType)
        assert len(worker_types) == 3
        print_success("WorkerType enum has correct number of values")
        
        return True
        
    except Exception as e:
        print_error(f"Worker type validation failed: {e}")
        traceback.print_exc()
        return False


async def validate_system_integration():
    """Validate system integration functionality"""
    print_header("System Integration Validation")
    
    try:
        # Create test configuration
        config = SystemConfiguration(
            server_port=8773,  # Use different port for testing
            enable_monitoring=False,
            enable_error_recovery=False,
            log_level="ERROR"
        )
        print_success("Test configuration created")
        
        # Create system integration
        system = SystemIntegration(config)
        assert system.state.value == "uninitialized"
        print_success("System integration instance created")
        
        # Test system status
        status = system.get_system_status()
        assert "state" in status
        assert "components" in status
        assert "configuration" in status
        print_success("System status retrieval works")
        
        # Test component dependencies
        assert system._component_dependencies is not None
        assert len(system._component_dependencies) > 0
        print_success("Component dependencies configured")
        
        return True
        
    except Exception as e:
        print_error(f"System integration validation failed: {e}")
        traceback.print_exc()
        return False


def validate_startup_system():
    """Validate system startup functionality"""
    print_header("System Startup Validation")
    
    try:
        # Create startup options
        options = StartupOptions(
            environment="testing",
            log_level="ERROR",
            enable_monitoring=False,
            enable_error_recovery=False
        )
        print_success("Startup options created")
        
        # Create startup system
        startup = SystemStartup(options)
        assert startup.options.environment == "testing"
        print_success("System startup instance created")
        
        # Test configuration loading
        config = startup.load_configuration()
        assert config is not None
        print_success("Configuration loading works")
        
        # Test requirements validation
        result = startup.validate_system_requirements()
        assert result is True
        print_success("System requirements validation passed")
        
        return True
        
    except Exception as e:
        print_error(f"System startup validation failed: {e}")
        traceback.print_exc()
        return False


def validate_v1_compatibility():
    """Validate v1 compatibility layer"""
    print_header("V1 Compatibility Validation")
    
    try:
        # Test create_worker function exists
        assert callable(create_worker)
        print_success("create_worker function available")
        
        # Test worker creation (mocked)
        try:
            from unittest.mock import patch, Mock
            
            with patch('botted_library.compatibility.v1_compatibility.Worker') as mock_worker_class:
                mock_worker = Mock()
                mock_worker.call = Mock(return_value="test result")
                mock_worker_class.return_value = mock_worker
                
                worker = create_worker("TestWorker", "Test Role", "Test job description")
                assert worker is not None
                print_success("Worker creation works")
                
                # Test worker.call method
                result = worker.call("test task")
                assert result == "test result"
                print_success("Worker.call method works")
                
        except ImportError:
            print_info("Mock not available, skipping detailed v1 compatibility test")
        
        return True
        
    except Exception as e:
        print_error(f"V1 compatibility validation failed: {e}")
        traceback.print_exc()
        return False


def validate_environment_configs():
    """Validate environment-specific configurations"""
    print_header("Environment Configuration Validation")
    
    try:
        config_dir = Path("botted_library/config")
        
        # Check if config files exist
        dev_config = config_dir / "development.json"
        prod_config = config_dir / "production.json"
        test_config = config_dir / "testing.json"
        
        if dev_config.exists():
            print_success("Development configuration file exists")
        else:
            print_info("Development configuration file not found")
        
        if prod_config.exists():
            print_success("Production configuration file exists")
        else:
            print_info("Production configuration file not found")
        
        if test_config.exists():
            print_success("Testing configuration file exists")
        else:
            print_info("Testing configuration file not found")
        
        return True
        
    except Exception as e:
        print_error(f"Environment configuration validation failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Main validation function"""
    print_header("Botted Library v2 System Validation")
    print_info("Validating integrated system components...")
    
    validation_results = []
    
    # Run all validations
    validation_results.append(("Import Validation", validate_imports()))
    validation_results.append(("Configuration Validation", validate_configuration()))
    validation_results.append(("Worker Type Validation", validate_worker_types()))
    validation_results.append(("System Integration Validation", await validate_system_integration()))
    validation_results.append(("System Startup Validation", validate_startup_system()))
    validation_results.append(("V1 Compatibility Validation", validate_v1_compatibility()))
    validation_results.append(("Environment Config Validation", validate_environment_configs()))
    
    # Print summary
    print_header("Validation Summary")
    
    passed = 0
    failed = 0
    
    for test_name, result in validation_results:
        if result:
            print_success(f"{test_name}: PASSED")
            passed += 1
        else:
            print_error(f"{test_name}: FAILED")
            failed += 1
    
    print(f"\nTotal: {len(validation_results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print_header("🎉 All Validations Passed!")
        print_success("The Botted Library v2 system integration is working correctly!")
        print_info("The system is ready for collaborative AI work.")
        return True
    else:
        print_header("❌ Some Validations Failed")
        print_error(f"{failed} validation(s) failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during validation: {e}")
        traceback.print_exc()
        sys.exit(1)
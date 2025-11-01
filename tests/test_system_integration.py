"""
Comprehensive system integration tests for Botted Library v2

Tests the complete system assembly, configuration, and end-to-end functionality.
"""

import pytest
import asyncio
import threading
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from botted_library.core.system_integration import (
    SystemIntegration, SystemConfiguration, SystemState,
    get_system_integration, initialize_v2_system, shutdown_v2_system
)
from botted_library.core.system_startup import (
    SystemStartup, StartupOptions, quick_start_system
)
from botted_library.core.configuration_manager import (
    ConfigurationManager, ConfigurationSchema, ConfigurationError
)
from botted_library.core.interfaces import WorkerType


class TestSystemIntegration:
    """Test system integration functionality"""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing"""
        return SystemConfiguration(
            server_host="localhost",
            server_port=8766,  # Different port for testing
            server_max_connections=10,
            max_workers_per_type={
                WorkerType.PLANNER: 2,
                WorkerType.EXECUTOR: 5,
                WorkerType.VERIFIER: 3
            },
            enable_monitoring=False,  # Disable for testing
            enable_error_recovery=True,
            log_level="ERROR"  # Reduce log noise
        )
    
    @pytest.fixture
    def system_integration(self, sample_config):
        """Create system integration instance for testing"""
        return SystemIntegration(sample_config)
    
    def test_system_initialization(self, system_integration):
        """Test system initialization"""
        assert system_integration.state == SystemState.UNINITIALIZED
        assert system_integration.config is not None
        assert system_integration.logger is not None
        
        # Check component dependencies are set up
        assert system_integration._component_dependencies is not None
        assert len(system_integration._component_dependencies) > 0
    
    @pytest.mark.asyncio
    async def test_system_startup_shutdown(self, system_integration):
        """Test complete system startup and shutdown cycle"""
        # Mock the components to avoid actual initialization
        with patch.multiple(
            system_integration,
            _initialize_error_recovery=AsyncMock(),
            _initialize_monitoring_system=AsyncMock(),
            _initialize_plugin_manager=AsyncMock(),
            _initialize_tool_manager=AsyncMock(),
            _initialize_worker_registry=AsyncMock(),
            _initialize_server=AsyncMock(),
            _initialize_mode_manager=AsyncMock(),
            _start_background_tasks=Mock()
        ):
            # Test initialization
            success = await system_integration.initialize_system()
            assert success is True
            assert system_integration.state == SystemState.RUNNING
            
            # Test shutdown
            success = await system_integration.shutdown_system()
            assert success is True
            assert system_integration.state == SystemState.STOPPED
    
    @pytest.mark.asyncio
    async def test_system_initialization_failure(self, system_integration):
        """Test system initialization failure handling"""
        # Mock a component to fail initialization
        with patch.object(
            system_integration, 
            '_initialize_error_recovery',
            side_effect=Exception("Initialization failed")
        ):
            success = await system_integration.initialize_system()
            assert success is False
            assert system_integration.state == SystemState.ERROR
    
    def test_system_status(self, system_integration):
        """Test system status reporting"""
        status = system_integration.get_system_status()
        
        assert "state" in status
        assert "components" in status
        assert "metrics" in status
        assert "configuration" in status
        
        assert status["state"] == SystemState.UNINITIALIZED.value
        
        # Check configuration in status
        config = status["configuration"]
        assert config["server_host"] == "localhost"
        assert config["server_port"] == 8766
    
    def test_component_access(self, system_integration):
        """Test component access methods"""
        # Initially should be None
        assert system_integration.get_server() is None
        assert system_integration.get_worker_registry() is None
        assert system_integration.get_mode_manager() is None
        
        # Test is_running
        assert system_integration.is_running() is False
    
    def test_callback_management(self, system_integration):
        """Test initialization and shutdown callbacks"""
        init_called = False
        shutdown_called = False
        
        def init_callback():
            nonlocal init_called
            init_called = True
        
        def shutdown_callback():
            nonlocal shutdown_called
            shutdown_called = True
        
        system_integration.add_initialization_callback(init_callback)
        system_integration.add_shutdown_callback(shutdown_callback)
        
        # Callbacks should be added
        assert init_callback in system_integration._initialization_callbacks
        assert shutdown_callback in system_integration._shutdown_callbacks


class TestSystemStartup:
    """Test system startup functionality"""
    
    @pytest.fixture
    def startup_options(self):
        """Create startup options for testing"""
        return StartupOptions(
            environment="testing",
            log_level="ERROR",
            enable_monitoring=False,
            enable_error_recovery=True,
            background_mode=False
        )
    
    @pytest.fixture
    def system_startup(self, startup_options):
        """Create system startup instance"""
        return SystemStartup(startup_options)
    
    def test_startup_initialization(self, system_startup):
        """Test startup initialization"""
        assert system_startup.options is not None
        assert system_startup.logger is not None
        assert system_startup.options.environment == "testing"
        assert system_startup.options.log_level == "ERROR"
    
    def test_configuration_loading(self, system_startup):
        """Test configuration loading from various sources"""
        config = system_startup.load_configuration()
        
        assert isinstance(config, SystemConfiguration)
        assert config.log_level == "ERROR"  # From startup options
        assert config.enable_monitoring is False  # From startup options
    
    def test_environment_configuration_loading(self, system_startup):
        """Test loading configuration from environment variables"""
        with patch.dict('os.environ', {
            'BOTTED_SERVER_HOST': 'test-host',
            'BOTTED_SERVER_PORT': '9999',
            'BOTTED_MAX_PLANNERS': '3'
        }):
            config = system_startup.load_configuration()
            
            assert config.server_host == 'test-host'
            assert config.server_port == 9999
            assert config.max_workers_per_type[WorkerType.PLANNER] == 3
    
    def test_configuration_file_loading(self, system_startup):
        """Test loading configuration from file"""
        # Create temporary config file
        config_data = {
            "server_host": "file-host",
            "server_port": 7777,
            "log_level": "DEBUG"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            system_startup.options.config_file = config_file
            config = system_startup.load_configuration()
            
            assert config.server_host == "file-host"
            assert config.server_port == 7777
            # log_level should be overridden by startup options
            assert config.log_level == "ERROR"
        finally:
            Path(config_file).unlink()
    
    def test_system_requirements_validation(self, system_startup):
        """Test system requirements validation"""
        # Should pass basic validation
        result = system_startup.validate_system_requirements()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_startup_system_lifecycle(self, system_startup):
        """Test complete startup system lifecycle"""
        # Mock system integration to avoid actual startup
        with patch('botted_library.core.system_startup.get_system_integration') as mock_get_system:
            mock_system = Mock()
            mock_system.initialize_system = AsyncMock(return_value=True)
            mock_system.shutdown_system = AsyncMock(return_value=True)
            mock_system.get_system_status = Mock(return_value={
                'state': 'running',
                'components': {},
                'metrics': {},
                'configuration': {
                    'server_host': 'localhost',
                    'server_port': 8765,
                    'max_workers': {},
                    'monitoring_enabled': False,
                    'error_recovery_enabled': True
                }
            })
            mock_get_system.return_value = mock_system
            
            # Test startup
            system = await system_startup.start_system()
            assert system is not None
            mock_system.initialize_system.assert_called_once()
            
            # Test shutdown
            success = await system_startup.stop_system()
            assert success is True
            mock_system.shutdown_system.assert_called_once()


class TestConfigurationManager:
    """Test configuration management functionality"""
    
    @pytest.fixture
    def config_manager(self):
        """Create configuration manager for testing"""
        return ConfigurationManager()
    
    def test_configuration_initialization(self, config_manager):
        """Test configuration manager initialization"""
        assert config_manager._config is not None
        assert isinstance(config_manager._config, ConfigurationSchema)
        assert len(config_manager._validation_rules) > 0
    
    def test_configuration_validation(self, config_manager):
        """Test configuration validation"""
        # Valid configuration should pass
        config_manager._validate_configuration()
        
        # Invalid configuration should fail
        config_manager._config.server_port = -1  # Invalid port
        
        with pytest.raises(ConfigurationError):
            config_manager._validate_configuration()
    
    def test_configuration_get_set(self, config_manager):
        """Test getting and setting configuration values"""
        # Test getting values
        host = config_manager.get_value("server_host")
        assert host == "localhost"
        
        # Test setting values
        config_manager.set_value("server_host", "new-host")
        assert config_manager.get_value("server_host") == "new-host"
        
        # Test nested values
        config_manager.set_value("max_workers_per_type.PLANNER", 10)
        assert config_manager.get_value("max_workers_per_type.PLANNER") == 10
    
    def test_configuration_file_operations(self, config_manager):
        """Test configuration file save/load operations"""
        # Modify configuration
        config_manager.set_value("server_host", "test-host")
        config_manager.set_value("server_port", 9999)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
        
        try:
            config_manager.save_to_file(config_file)
            
            # Verify file was created and contains correct data
            with open(config_file, 'r') as f:
                saved_config = json.load(f)
            
            assert saved_config["server_host"] == "test-host"
            assert saved_config["server_port"] == 9999
        finally:
            Path(config_file).unlink()
    
    def test_configuration_change_callbacks(self, config_manager):
        """Test configuration change callbacks"""
        callback_called = False
        callback_key = None
        callback_old_value = None
        callback_new_value = None
        
        def change_callback(key, old_value, new_value):
            nonlocal callback_called, callback_key, callback_old_value, callback_new_value
            callback_called = True
            callback_key = key
            callback_old_value = old_value
            callback_new_value = new_value
        
        config_manager.add_change_callback(change_callback)
        
        # Make a change
        config_manager.set_value("server_host", "callback-test")
        
        assert callback_called is True
        assert callback_key == "server_host"
        assert callback_new_value == "callback-test"
    
    def test_configuration_history(self, config_manager):
        """Test configuration change history"""
        initial_history_length = len(config_manager.get_configuration_history())
        
        # Make some changes
        config_manager.set_value("server_host", "history-test-1")
        config_manager.set_value("server_port", 8888)
        
        history = config_manager.get_configuration_history()
        assert len(history) > initial_history_length
        
        # Check history entries have required fields
        for entry in history:
            assert "timestamp" in entry
            assert "reason" in entry
            assert "config" in entry


class TestEndToEndIntegration:
    """Test complete end-to-end system integration"""
    
    @pytest.mark.asyncio
    async def test_quick_start_system(self):
        """Test quick start system functionality"""
        # Create temporary config file
        config_data = {
            "environment": "testing",
            "server_port": 8767,  # Different port
            "log_level": "ERROR",
            "enable_monitoring": False,
            "test_mode": True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            # Mock the system components to avoid actual startup
            with patch('botted_library.core.system_startup.SystemStartup') as mock_startup_class:
                mock_startup = Mock()
                mock_startup.validate_system_requirements = Mock(return_value=True)
                mock_startup.start_system = AsyncMock()
                
                mock_system = Mock()
                mock_startup.start_system.return_value = mock_system
                mock_startup_class.return_value = mock_startup
                
                # Test quick start
                system = await quick_start_system(config_file)
                
                assert system is not None
                mock_startup.validate_system_requirements.assert_called_once()
                mock_startup.start_system.assert_called_once()
        finally:
            Path(config_file).unlink()
    
    def test_global_system_management(self):
        """Test global system instance management"""
        # Test getting system integration instance
        system1 = get_system_integration()
        system2 = get_system_integration()
        
        # Should return the same instance
        assert system1 is system2
    
    @pytest.mark.asyncio
    async def test_system_initialization_and_shutdown_functions(self):
        """Test global system initialization and shutdown functions"""
        config = SystemConfiguration(
            server_port=8768,  # Different port
            enable_monitoring=False,
            log_level="ERROR"
        )
        
        # Mock the system to avoid actual initialization
        with patch('botted_library.core.system_integration.SystemIntegration') as mock_system_class:
            mock_system = Mock()
            mock_system.initialize_system = AsyncMock(return_value=True)
            mock_system.shutdown_system = AsyncMock(return_value=True)
            mock_system_class.return_value = mock_system
            
            # Test initialization
            system = initialize_v2_system(config)
            assert system is not None
            mock_system.initialize_system.assert_called_once()
            
            # Test shutdown
            success = shutdown_v2_system()
            assert success is True
            mock_system.shutdown_system.assert_called_once()


class TestSystemPerformance:
    """Test system performance and scalability"""
    
    def test_configuration_performance(self):
        """Test configuration manager performance"""
        config_manager = ConfigurationManager()
        
        # Test rapid configuration changes
        start_time = time.time()
        for i in range(100):
            config_manager.set_value("server_port", 8000 + i)
        end_time = time.time()
        
        # Should complete quickly (less than 1 second for 100 changes)
        assert (end_time - start_time) < 1.0
    
    def test_concurrent_configuration_access(self):
        """Test concurrent configuration access"""
        config_manager = ConfigurationManager()
        results = []
        errors = []
        
        def worker_thread(thread_id):
            try:
                for i in range(10):
                    config_manager.set_value(f"test_key_{thread_id}", i)
                    value = config_manager.get_value(f"test_key_{thread_id}")
                    results.append((thread_id, value))
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have no errors
        assert len(errors) == 0
        # Should have results from all threads
        assert len(results) == 50  # 5 threads * 10 operations each


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
Tests for V1 Compatibility Layer

Tests that v1 interfaces work correctly with v2 collaborative features
and that backward compatibility is maintained.
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from botted_library.compatibility.v1_compatibility import (
    Worker,
    create_worker,
    enable_collaborative_features,
    disable_collaborative_features,
    get_compatibility_status,
    _compatibility_manager
)


class TestV1CompatibilityLayer:
    """Test the v1 compatibility layer functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Reset compatibility manager state
        _compatibility_manager._collaborative_enabled = True
        _compatibility_manager._server_started = False
        _compatibility_manager._v1_workers.clear()
    
    def test_create_worker_interface_compatibility(self):
        """Test that create_worker maintains v1 interface."""
        # Test with minimal parameters (v1 style)
        worker = create_worker(
            name="TestWorker",
            role="Test Role",
            job_description="Test description"
        )
        
        assert worker.name == "TestWorker"
        assert worker.role == "Test Role"
        assert worker.job_description == "Test description"
        assert hasattr(worker, 'call')
        assert hasattr(worker, 'get_history')
        assert hasattr(worker, 'get_status')
    
    def test_create_worker_with_config(self):
        """Test create_worker with configuration (v1 style)."""
        config = {
            'llm': {'provider': 'test'},
            'browser': {'headless': True}
        }
        
        worker = create_worker(
            name="ConfigWorker",
            role="Configured Role",
            job_description="Configured worker",
            config=config
        )
        
        assert worker.config['llm']['provider'] == 'test'
        assert worker.config['browser']['headless'] is True
    
    @patch('botted_library.compatibility.v1_compatibility._compatibility_manager')
    def test_worker_call_interface_compatibility(self, mock_manager):
        """Test that worker.call() maintains v1 interface."""
        # Mock the compatibility manager
        mock_manager._collaborative_enabled = False
        mock_manager._server_started = False
        
        with patch('botted_library.simple_worker.Worker') as mock_v1_worker:
            # Setup mock v1 worker
            mock_instance = Mock()
            mock_instance.name = "TestWorker"
            mock_instance.role = "Test Role"
            mock_instance.job_description = "Test description"
            mock_instance.config = {}
            mock_instance._worker_id = "test_id"
            mock_instance.call.return_value = {
                'success': True,
                'summary': 'Task completed',
                'deliverables': {}
            }
            mock_v1_worker.return_value = mock_instance
            
            worker = Worker("TestWorker", "Test Role", "Test description")
            
            # Test call method
            result = worker.call("Test task")
            
            # Verify v1 interface is maintained
            assert isinstance(result, dict)
            assert 'success' in result
            assert 'collaborative_features_used' in result
            
            # Verify underlying v1 worker was called
            mock_instance.call.assert_called_once_with("Test task")
    
    def test_collaborative_features_automatic_enablement(self):
        """Test that collaborative features are automatically enabled."""
        with patch('botted_library.compatibility.v1_compatibility._compatibility_manager') as mock_manager:
            mock_manager._collaborative_enabled = True
            mock_manager._server_started = True
            mock_manager.ensure_server_running = Mock()
            mock_manager.register_v1_worker = Mock()
            
            with patch('botted_library.simple_worker.Worker') as mock_v1_worker:
                mock_instance = Mock()
                mock_instance.name = "TestWorker"
                mock_instance.role = "Test Role"
                mock_instance.job_description = "Test description"
                mock_instance.config = {}
                mock_instance._worker_id = "test_id"
                mock_v1_worker.return_value = mock_instance
                
                worker = Worker("TestWorker", "Test Role", "Test description")
                
                # Verify server startup was attempted
                mock_manager.ensure_server_running.assert_called_once()
                
                # Verify worker was registered for collaborative features
                mock_manager.register_v1_worker.assert_called_once()
    
    def test_enable_disable_collaborative_features(self):
        """Test enabling and disabling collaborative features."""
        # Test enable
        with patch.object(_compatibility_manager, 'enable_collaborative_features') as mock_enable:
            mock_enable.return_value = True
            result = enable_collaborative_features()
            assert result is True
            mock_enable.assert_called_once()
        
        # Test disable
        with patch.object(_compatibility_manager, 'disable_collaborative_features') as mock_disable:
            disable_collaborative_features()
            mock_disable.assert_called_once()
    
    def test_get_compatibility_status(self):
        """Test getting compatibility status."""
        with patch.object(_compatibility_manager, 'get_status') as mock_status:
            mock_status.return_value = {
                'collaborative_enabled': True,
                'server_running': True,
                'v1_workers_count': 2
            }
            
            status = get_compatibility_status()
            
            assert status['collaborative_enabled'] is True
            assert status['server_running'] is True
            assert status['v1_workers_count'] == 2
            mock_status.assert_called_once()
    
    def test_worker_collaborative_methods(self):
        """Test that collaborative methods are available on v1 workers."""
        with patch('botted_library.simple_worker.Worker') as mock_v1_worker:
            mock_instance = Mock()
            mock_instance.name = "TestWorker"
            mock_instance.role = "Test Role"
            mock_instance.job_description = "Test description"
            mock_instance.config = {}
            mock_instance._worker_id = "test_id"
            
            # Mock collaborative methods
            mock_instance.get_active_workers.return_value = []
            mock_instance.delegate_task.return_value = {'success': True}
            mock_instance.ask_for_help.return_value = "Help provided"
            mock_instance.get_collaboration_history.return_value = []
            
            mock_v1_worker.return_value = mock_instance
            
            worker = Worker("TestWorker", "Test Role", "Test description")
            
            # Test collaborative methods are available
            assert hasattr(worker, 'get_active_workers')
            assert hasattr(worker, 'delegate_task')
            assert hasattr(worker, 'ask_for_help')
            assert hasattr(worker, 'get_collaboration_history')
            
            # Test methods work
            collaborators = worker.get_active_workers()
            assert isinstance(collaborators, list)
            
            result = worker.delegate_task("Test task")
            assert result['success'] is True
            
            help_response = worker.ask_for_help("Need help")
            assert help_response == "Help provided"
            
            history = worker.get_collaboration_history()
            assert isinstance(history, list)
    
    def test_worker_shutdown_compatibility(self):
        """Test that worker shutdown works correctly."""
        with patch('botted_library.simple_worker.Worker') as mock_v1_worker:
            mock_instance = Mock()
            mock_instance.name = "TestWorker"
            mock_instance.role = "Test Role"
            mock_instance.job_description = "Test description"
            mock_instance.config = {}
            mock_instance._worker_id = "test_id"
            mock_instance.shutdown = Mock()
            
            mock_v1_worker.return_value = mock_instance
            
            with patch.object(_compatibility_manager, 'unregister_v1_worker') as mock_unregister:
                worker = Worker("TestWorker", "Test Role", "Test description")
                worker.shutdown()
                
                # Verify worker was unregistered and shutdown
                mock_unregister.assert_called_once_with("test_id")
                mock_instance.shutdown.assert_called_once()


class TestCompatibilityManager:
    """Test the CompatibilityManager class."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Create fresh compatibility manager for testing
        from botted_library.compatibility.v1_compatibility import CompatibilityManager
        self.manager = CompatibilityManager()
    
    def test_server_startup(self):
        """Test collaborative server startup."""
        with patch('botted_library.compatibility.v1_compatibility.get_global_server') as mock_get_server:
            mock_server = Mock()
            mock_server.state.value = "stopped"
            mock_server.start_server = Mock()
            mock_get_server.return_value = mock_server
            
            self.manager.ensure_server_running()
            
            # Verify server was started
            mock_get_server.assert_called_once()
            mock_server.start_server.assert_called_once()
            assert self.manager._server_started is True
    
    def test_server_startup_failure_handling(self):
        """Test handling of server startup failures."""
        with patch('botted_library.compatibility.v1_compatibility.get_global_server') as mock_get_server:
            mock_get_server.side_effect = Exception("Server startup failed")
            
            # Should not raise exception, but disable collaborative features
            self.manager.ensure_server_running()
            
            assert self.manager._collaborative_enabled is False
    
    def test_worker_registration(self):
        """Test v1 worker registration with server."""
        mock_worker = Mock()
        mock_worker.name = "TestWorker"
        mock_worker.role = "Test Role"
        mock_worker.job_description = "Test description"
        mock_worker._get_capabilities.return_value = ['thinking', 'web_search']
        
        with patch.object(self.manager, '_server') as mock_server:
            self.manager._server_started = True
            self.manager._collaborative_enabled = True
            
            self.manager.register_v1_worker("test_id", mock_worker)
            
            # Verify worker was registered with server
            mock_server.register_worker.assert_called_once()
            
            # Verify worker info was properly formatted
            call_args = mock_server.register_worker.call_args
            worker_info = call_args[0][1]
            assert worker_info['name'] == "TestWorker"
            assert worker_info['role'] == "Test Role"
            assert worker_info['v1_compatibility'] is True
    
    def test_worker_unregistration(self):
        """Test v1 worker unregistration."""
        # Register a worker first
        self.manager._v1_workers["test_id"] = Mock()
        
        with patch.object(self.manager, '_server') as mock_server:
            self.manager._server_started = True
            
            self.manager.unregister_v1_worker("test_id")
            
            # Verify worker was removed from tracking
            assert "test_id" not in self.manager._v1_workers
            
            # Verify server unregistration was called
            mock_server.unregister_worker.assert_called_once_with("test_id")
    
    def test_enable_collaborative_features(self):
        """Test enabling collaborative features."""
        with patch.object(self.manager, 'ensure_server_running') as mock_ensure:
            with patch.object(self.manager, 'register_v1_worker') as mock_register:
                # Add some workers to test registration
                mock_worker = Mock()
                self.manager._v1_workers["test_id"] = mock_worker
                
                result = self.manager.enable_collaborative_features()
                
                # Verify server startup was attempted
                mock_ensure.assert_called_once()
                
                # Verify existing workers were registered
                mock_register.assert_called_once_with("test_id", mock_worker)
    
    def test_disable_collaborative_features(self):
        """Test disabling collaborative features."""
        self.manager._collaborative_enabled = True
        
        self.manager.disable_collaborative_features()
        
        assert self.manager._collaborative_enabled is False
    
    def test_get_status(self):
        """Test getting compatibility manager status."""
        self.manager._collaborative_enabled = True
        self.manager._server_started = True
        self.manager._v1_workers = {"worker1": Mock(), "worker2": Mock()}
        
        with patch.object(self.manager, '_server') as mock_server:
            mock_server.get_server_status.return_value = {"status": "running"}
            
            status = self.manager.get_status()
            
            assert status['collaborative_enabled'] is True
            assert status['server_running'] is True
            assert status['v1_workers_count'] == 2
            assert status['server_status'] == {"status": "running"}


class TestCollaborativeContextIntegration:
    """Test integration of collaborative context with v1 workers."""
    
    def test_collaborative_context_addition(self):
        """Test that collaborative context is added to task instructions."""
        with patch('botted_library.simple_worker.Worker') as mock_v1_worker:
            mock_instance = Mock()
            mock_instance.name = "TestWorker"
            mock_instance.role = "Test Role"
            mock_instance.job_description = "Test description"
            mock_instance.config = {}
            mock_instance._worker_id = "test_id"
            mock_instance.get_active_workers.return_value = [
                {'name': 'Alice', 'role': 'Researcher'},
                {'name': 'Bob', 'role': 'Writer'}
            ]
            mock_instance.call.return_value = {'success': True}
            
            mock_v1_worker.return_value = mock_instance
            
            with patch('botted_library.compatibility.v1_compatibility._compatibility_manager') as mock_manager:
                mock_manager._collaborative_enabled = True
                mock_manager._server_started = True
                
                worker = Worker("TestWorker", "Test Role", "Test description")
                worker.call("Test task")
                
                # Verify call was made with enhanced instructions
                call_args = mock_instance.call.call_args[0][0]
                assert "COLLABORATIVE CONTEXT" in call_args
                assert "Alice (Researcher)" in call_args
                assert "delegate_task()" in call_args
    
    def test_collaborative_metadata_in_results(self):
        """Test that collaborative metadata is added to results."""
        with patch('botted_library.simple_worker.Worker') as mock_v1_worker:
            mock_instance = Mock()
            mock_instance.name = "TestWorker"
            mock_instance.role = "Test Role"
            mock_instance.job_description = "Test description"
            mock_instance.config = {}
            mock_instance._worker_id = "test_id"
            mock_instance.get_active_workers.return_value = [{'name': 'Alice'}]
            mock_instance.call.return_value = {'success': True, 'summary': 'Done'}
            
            mock_v1_worker.return_value = mock_instance
            
            with patch('botted_library.compatibility.v1_compatibility._compatibility_manager') as mock_manager:
                mock_manager._collaborative_enabled = True
                mock_manager._server_started = True
                
                worker = Worker("TestWorker", "Test Role", "Test description")
                result = worker.call("Test task")
                
                # Verify collaborative metadata was added
                assert result['collaborative_features_used'] is True
                assert result['available_collaborators'] == 1
                assert result['success'] is True  # Original result preserved
    
    def test_fallback_to_v1_behavior(self):
        """Test fallback to v1 behavior when collaborative features unavailable."""
        with patch('botted_library.simple_worker.Worker') as mock_v1_worker:
            mock_instance = Mock()
            mock_instance.name = "TestWorker"
            mock_instance.role = "Test Role"
            mock_instance.job_description = "Test description"
            mock_instance.config = {}
            mock_instance._worker_id = "test_id"
            mock_instance.call.return_value = {'success': True, 'summary': 'Done'}
            
            mock_v1_worker.return_value = mock_instance
            
            with patch('botted_library.compatibility.v1_compatibility._compatibility_manager') as mock_manager:
                mock_manager._collaborative_enabled = False
                mock_manager._server_started = False
                
                worker = Worker("TestWorker", "Test Role", "Test description")
                result = worker.call("Test task")
                
                # Verify fallback to v1 behavior
                assert result['collaborative_features_used'] is False
                assert result['success'] is True  # Original result preserved
                
                # Verify original instructions were used (no collaborative context)
                call_args = mock_instance.call.call_args[0][0]
                assert call_args == "Test task"
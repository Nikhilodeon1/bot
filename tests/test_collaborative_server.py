"""
Unit tests for CollaborativeServer

Tests the core server infrastructure including lifecycle management,
worker registration, and message routing.
"""

import unittest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from botted_library.core.collaborative_server import (
    CollaborativeServer, ServerConfig, ServerState,
    get_global_server, shutdown_global_server
)
from botted_library.core.exceptions import WorkerError


class TestCollaborativeServer(unittest.TestCase):
    """Test cases for CollaborativeServer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = ServerConfig(
            host="localhost",
            port=8765,
            max_workers=10,
            message_queue_size=100,
            heartbeat_interval=5,
            auto_cleanup=True,
            log_level="DEBUG"
        )
        self.server = CollaborativeServer(self.config)
    
    def tearDown(self):
        """Clean up after tests"""
        if self.server.state == ServerState.RUNNING:
            self.server.stop_server()
    
    def test_server_initialization(self):
        """Test server initialization"""
        self.assertEqual(self.server.state, ServerState.STOPPED)
        self.assertEqual(self.server.config.host, "localhost")
        self.assertEqual(self.server.config.port, 8765)
        self.assertEqual(self.server.config.max_workers, 10)
        self.assertIsNotNone(self.server.server_id)
        self.assertIsNone(self.server.start_time)
    
    @patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry')
    @patch('botted_library.core.message_router.MessageRouter')
    def test_server_startup_success(self, mock_message_router, mock_worker_registry):
        """Test successful server startup"""
        # Mock the components
        mock_registry = Mock()
        mock_router = Mock()
        mock_worker_registry.return_value = mock_registry
        mock_message_router.return_value = mock_router
        
        # Start server
        self.server.start_server()
        
        # Verify state
        self.assertEqual(self.server.state, ServerState.RUNNING)
        self.assertIsNotNone(self.server.start_time)
        self.assertIsNotNone(self.server._worker_registry)
        self.assertIsNotNone(self.server._message_router)
        
        # Verify components were initialized
        mock_worker_registry.assert_called_once_with(server_instance=self.server)
        mock_message_router.assert_called_once()
    
    def test_server_startup_already_running(self):
        """Test server startup when already running"""
        self.server.state = ServerState.RUNNING
        
        with self.assertRaises(WorkerError) as context:
            self.server.start_server()
        
        self.assertIn("Cannot start server in state: running", str(context.exception))
    
    @patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry')
    @patch('botted_library.core.message_router.MessageRouter')
    def test_server_shutdown_success(self, mock_message_router, mock_worker_registry):
        """Test successful server shutdown"""
        # Mock the components
        mock_registry = Mock()
        mock_router = Mock()
        mock_worker_registry.return_value = mock_registry
        mock_message_router.return_value = mock_router
        
        # Start and then stop server
        self.server.start_server()
        self.server.stop_server()
        
        # Verify state
        self.assertEqual(self.server.state, ServerState.STOPPED)
        
        # Verify cleanup was called
        mock_router.shutdown.assert_called_once()
        mock_registry.shutdown.assert_called_once()
    
    def test_server_shutdown_not_running(self):
        """Test server shutdown when not running"""
        # Should not raise an error, just log a warning
        self.server.stop_server()
        self.assertEqual(self.server.state, ServerState.STOPPED)
    
    @patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry')
    @patch('botted_library.core.message_router.MessageRouter')
    def test_worker_registration_success(self, mock_message_router, mock_worker_registry):
        """Test successful worker registration"""
        # Setup mocks
        mock_registry = Mock()
        mock_registry.register_specialized_worker.return_value = "reg_123"
        mock_worker_registry.return_value = mock_registry
        mock_message_router.return_value = Mock()
        
        # Start server
        self.server.start_server()
        
        # Register worker
        worker_info = {
            'name': 'TestWorker',
            'role': 'Test Role',
            'worker_type': 'executor',
            'capabilities': ['testing']
        }
        
        registration_id = self.server.register_worker('worker_123', worker_info)
        
        # Verify registration
        self.assertEqual(registration_id, "reg_123")
        mock_registry.register_specialized_worker.assert_called_once_with(
            worker_id='worker_123',
            worker_info=worker_info
        )
        self.assertEqual(self.server.stats['workers_registered'], 1)
    
    def test_worker_registration_server_not_running(self):
        """Test worker registration when server not running"""
        worker_info = {'name': 'TestWorker'}
        
        with self.assertRaises(WorkerError) as context:
            self.server.register_worker('worker_123', worker_info)
        
        self.assertIn("Cannot register worker - server not running", str(context.exception))
    
    @patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry')
    @patch('botted_library.core.message_router.MessageRouter')
    def test_worker_unregistration(self, mock_message_router, mock_worker_registry):
        """Test worker unregistration"""
        # Setup mocks
        mock_registry = Mock()
        mock_worker_registry.return_value = mock_registry
        mock_message_router.return_value = Mock()
        
        # Start server
        self.server.start_server()
        
        # Unregister worker
        self.server.unregister_worker('worker_123')
        
        # Verify unregistration
        mock_registry.unregister_worker.assert_called_once_with('worker_123')
    
    @patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry')
    @patch('botted_library.core.message_router.MessageRouter')
    def test_message_routing_success(self, mock_message_router, mock_worker_registry):
        """Test successful message routing"""
        # Setup mocks
        mock_router = Mock()
        mock_router.route_message.return_value = True
        mock_message_router.return_value = mock_router
        mock_worker_registry.return_value = Mock()
        
        # Start server
        self.server.start_server()
        
        # Route message
        message = {'content': 'test message'}
        success = self.server.route_message('worker_1', 'worker_2', message)
        
        # Verify routing
        self.assertTrue(success)
        mock_router.route_message.assert_called_once_with('worker_1', 'worker_2', message)
        self.assertEqual(self.server.stats['messages_routed'], 1)
    
    def test_message_routing_server_not_running(self):
        """Test message routing when server not running"""
        message = {'content': 'test message'}
        
        with self.assertRaises(WorkerError) as context:
            self.server.route_message('worker_1', 'worker_2', message)
        
        self.assertIn("Cannot route message - server not running", str(context.exception))
    
    @patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry')
    @patch('botted_library.core.message_router.MessageRouter')
    def test_get_worker_registry(self, mock_message_router, mock_worker_registry):
        """Test getting worker registry"""
        # Setup mocks
        mock_registry = Mock()
        mock_worker_registry.return_value = mock_registry
        mock_message_router.return_value = Mock()
        
        # Start server
        self.server.start_server()
        
        # Get registry
        registry = self.server.get_worker_registry()
        
        # Verify registry
        self.assertEqual(registry, mock_registry)
    
    def test_get_worker_registry_not_available(self):
        """Test getting worker registry when not available"""
        with self.assertRaises(WorkerError) as context:
            self.server.get_worker_registry()
        
        self.assertIn("Worker registry not available", str(context.exception))
    
    @patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry')
    @patch('botted_library.core.message_router.MessageRouter')
    def test_get_server_status(self, mock_message_router, mock_worker_registry):
        """Test getting server status"""
        # Setup mocks
        mock_registry = Mock()
        mock_registry.get_active_workers.return_value = [{'worker_id': 'w1'}, {'worker_id': 'w2'}]
        mock_worker_registry.return_value = mock_registry
        mock_message_router.return_value = Mock()
        
        # Start server
        self.server.start_server()
        
        # Get status
        status = self.server.get_server_status()
        
        # Verify status
        self.assertEqual(status['server_id'], self.server.server_id)
        self.assertEqual(status['state'], ServerState.RUNNING.value)
        self.assertEqual(status['active_workers'], 2)
        self.assertEqual(status['config']['host'], 'localhost')
        self.assertEqual(status['config']['port'], 8765)
        self.assertIn('statistics', status)
        self.assertIn('uptime_seconds', status['statistics'])
    
    def test_server_config_defaults(self):
        """Test server configuration defaults"""
        default_config = ServerConfig()
        
        self.assertEqual(default_config.host, "localhost")
        self.assertEqual(default_config.port, 8765)
        self.assertEqual(default_config.max_workers, 100)
        self.assertEqual(default_config.message_queue_size, 1000)
        self.assertEqual(default_config.heartbeat_interval, 30)
        self.assertTrue(default_config.auto_cleanup)
        self.assertEqual(default_config.log_level, "INFO")


class TestGlobalServer(unittest.TestCase):
    """Test cases for global server management"""
    
    def tearDown(self):
        """Clean up global server after each test"""
        shutdown_global_server()
    
    def test_get_global_server_creates_instance(self):
        """Test that get_global_server creates a new instance"""
        server = get_global_server()
        
        self.assertIsInstance(server, CollaborativeServer)
        self.assertEqual(server.state, ServerState.STOPPED)
    
    def test_get_global_server_returns_same_instance(self):
        """Test that get_global_server returns the same instance"""
        server1 = get_global_server()
        server2 = get_global_server()
        
        self.assertIs(server1, server2)
    
    def test_get_global_server_with_config(self):
        """Test get_global_server with custom config"""
        config = ServerConfig(host="test_host", port=9999)
        server = get_global_server(config)
        
        self.assertEqual(server.config.host, "test_host")
        self.assertEqual(server.config.port, 9999)
    
    def test_shutdown_global_server(self):
        """Test shutting down global server"""
        # Create and start server
        server = get_global_server()
        
        # Mock the stop_server method to avoid actual startup
        with patch.object(server, 'stop_server') as mock_stop:
            shutdown_global_server()
            mock_stop.assert_called_once()
    
    def test_shutdown_global_server_no_instance(self):
        """Test shutting down when no global server exists"""
        # Should not raise an error
        shutdown_global_server()


class TestServerMaintenanceLoop(unittest.TestCase):
    """Test cases for server maintenance functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = ServerConfig(
            heartbeat_interval=1,  # Short interval for testing
            auto_cleanup=True
        )
        self.server = CollaborativeServer(self.config)
    
    def tearDown(self):
        """Clean up after tests"""
        if self.server.state == ServerState.RUNNING:
            self.server.stop_server()
    
    @patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry')
    @patch('botted_library.core.message_router.MessageRouter')
    def test_maintenance_loop_execution(self, mock_message_router, mock_worker_registry):
        """Test that maintenance loop executes periodically"""
        # Setup mocks
        mock_registry = Mock()
        mock_router = Mock()
        mock_worker_registry.return_value = mock_registry
        mock_message_router.return_value = mock_router
        
        # Start server
        self.server.start_server()
        
        # Wait for at least one maintenance cycle
        time.sleep(0.2)
        
        # Verify maintenance methods were called
        mock_registry.cleanup_inactive_workers.assert_called()
        mock_router.process_pending_messages.assert_called()
        
        # Stop server
        self.server.stop_server()
    
    @patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry')
    @patch('botted_library.core.message_router.MessageRouter')
    def test_server_thread_lifecycle(self, mock_message_router, mock_worker_registry):
        """Test server thread lifecycle"""
        # Setup mocks
        mock_worker_registry.return_value = Mock()
        mock_message_router.return_value = Mock()
        
        # Start server
        self.server.start_server()
        
        # Verify thread is running
        self.assertIsNotNone(self.server._server_thread)
        self.assertTrue(self.server._server_thread.is_alive())
        
        # Stop server
        self.server.stop_server()
        
        # Wait for thread to complete
        time.sleep(0.1)
        
        # Verify thread has stopped
        self.assertFalse(self.server._server_thread.is_alive())


if __name__ == '__main__':
    unittest.main()
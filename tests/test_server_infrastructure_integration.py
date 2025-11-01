"""
Integration tests for server infrastructure components

Tests the integration between CollaborativeServer, EnhancedWorkerRegistry,
and MessageRouter to ensure they work together correctly.
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch

from botted_library.core.collaborative_server import (
    CollaborativeServer, ServerConfig, ServerState
)
from botted_library.core.enhanced_worker_registry import WorkerType
from botted_library.core.message_router import MessageType, MessagePriority
from botted_library.core.exceptions import WorkerError


class TestServerInfrastructureIntegration(unittest.TestCase):
    """Integration tests for server infrastructure components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = ServerConfig(
            host="localhost",
            port=8765,
            max_workers=10,
            message_queue_size=50,
            heartbeat_interval=1,
            auto_cleanup=True,
            log_level="DEBUG"
        )
        self.server = CollaborativeServer(self.config)
    
    def tearDown(self):
        """Clean up after tests"""
        if self.server.state == ServerState.RUNNING:
            self.server.stop_server()
    
    def test_full_server_lifecycle_with_workers(self):
        """Test complete server lifecycle with worker registration"""
        # Start server
        self.server.start_server()
        self.assertEqual(self.server.state, ServerState.RUNNING)
        
        # Register workers of different types
        planner_info = {
            'name': 'TestPlanner',
            'role': 'Planning Specialist',
            'worker_type': 'planner',
            'capabilities': ['planning', 'strategy'],
            'enhanced_capabilities': [
                {'name': 'strategy_creation', 'level': 8, 'description': 'Create strategies'}
            ]
        }
        
        executor_info = {
            'name': 'TestExecutor',
            'role': 'Task Executor',
            'worker_type': 'executor',
            'capabilities': ['coding', 'testing'],
            'enhanced_capabilities': [
                {'name': 'python_coding', 'level': 9, 'description': 'Python development'}
            ]
        }
        
        verifier_info = {
            'name': 'TestVerifier',
            'role': 'Quality Verifier',
            'worker_type': 'verifier',
            'capabilities': ['validation', 'quality_control'],
            'enhanced_capabilities': [
                {'name': 'code_review', 'level': 7, 'description': 'Code quality review'}
            ]
        }
        
        # Register workers
        planner_reg_id = self.server.register_worker('planner_001', planner_info)
        executor_reg_id = self.server.register_worker('executor_001', executor_info)
        verifier_reg_id = self.server.register_worker('verifier_001', verifier_info)
        
        # Verify registrations
        self.assertIsNotNone(planner_reg_id)
        self.assertIsNotNone(executor_reg_id)
        self.assertIsNotNone(verifier_reg_id)
        
        # Get worker registry and verify workers
        registry = self.server.get_worker_registry()
        
        planners = registry.find_workers_by_type(WorkerType.PLANNER)
        executors = registry.find_workers_by_type(WorkerType.EXECUTOR)
        verifiers = registry.find_workers_by_type(WorkerType.VERIFIER)
        
        self.assertEqual(len(planners), 1)
        self.assertEqual(len(executors), 1)
        self.assertEqual(len(verifiers), 1)
        
        # Test message routing between workers
        task_message = {
            'message_type': MessageType.TASK_DELEGATION.value,
            'content': 'Implement user authentication',
            'priority': MessagePriority.HIGH.value,
            'requires_response': True
        }
        
        success = self.server.route_message('planner_001', 'executor_001', task_message)
        self.assertTrue(success)
        
        # Verify server statistics
        status = self.server.get_server_status()
        self.assertEqual(status['active_workers'], 3)
        self.assertEqual(status['statistics']['workers_registered'], 3)
        self.assertEqual(status['statistics']['messages_routed'], 1)
        
        # Stop server
        self.server.stop_server()
        self.assertEqual(self.server.state, ServerState.STOPPED)
    
    def test_worker_discovery_and_load_balancing(self):
        """Test worker discovery and load balancing functionality"""
        # Start server
        self.server.start_server()
        
        # Register multiple executor workers
        for i in range(3):
            executor_info = {
                'name': f'Executor{i+1}',
                'worker_type': 'executor',
                'capabilities': ['coding'],
                'enhanced_capabilities': [
                    {'name': 'coding', 'level': 7 + i, 'description': 'Coding tasks'}
                ],
                'max_concurrent_tasks': 2
            }
            self.server.register_worker(f'executor_{i+1:03d}', executor_info)
        
        # Get registry and test load balancing
        registry = self.server.get_worker_registry()
        
        # Find available executors
        available_executors = registry.find_workers_by_type(WorkerType.EXECUTOR, available_only=True)
        self.assertEqual(len(available_executors), 3)
        
        # Get load balanced worker for a task
        task_requirements = {
            'capabilities': ['coding'],
            'priority': 'high'
        }
        
        best_worker = registry.get_load_balanced_worker(WorkerType.EXECUTOR, task_requirements)
        self.assertIsNotNone(best_worker)
        
        # Simulate task assignment and completion
        worker_id = best_worker['worker_id']
        registry.complete_task_assignment(worker_id, success=True, completion_time=5.0)
        
        # Verify performance tracking
        stats = registry.get_registry_statistics()
        self.assertEqual(stats['total_workers'], 3)
        self.assertEqual(stats['workers_by_type']['executor'], 3)
        
        # Stop server
        self.server.stop_server()
    
    def test_flowchart_creation_and_management(self):
        """Test flowchart creation and management through registry"""
        # Start server
        self.server.start_server()
        
        # Register a planner worker
        planner_info = {
            'name': 'FlowchartPlanner',
            'worker_type': 'planner',
            'capabilities': ['planning', 'flowchart_creation']
        }
        self.server.register_worker('planner_001', planner_info)
        
        # Get registry and create flowchart
        registry = self.server.get_worker_registry()
        
        flowchart = registry.create_worker_flowchart(
            objectives="Implement user management system",
            created_by="planner_001",
            planner_count=1,
            executor_count=3,
            verifier_count=2
        )
        
        # Verify flowchart creation
        self.assertIsNotNone(flowchart.flowchart_id)
        self.assertEqual(flowchart.objectives, "Implement user management system")
        self.assertEqual(flowchart.planner_count, 1)
        self.assertEqual(flowchart.executor_count, 3)
        self.assertEqual(flowchart.verifier_count, 2)
        self.assertEqual(flowchart.status, "draft")
        
        # Activate flowchart
        success = registry.activate_flowchart(flowchart.flowchart_id)
        self.assertTrue(success)
        self.assertEqual(flowchart.status, "active")
        
        # Verify flowchart is in active set
        self.assertIn(flowchart.flowchart_id, registry.active_flowcharts)
        
        # Stop server
        self.server.stop_server()
    
    def test_message_routing_with_subscriptions(self):
        """Test message routing with real-time subscriptions"""
        # Start server
        self.server.start_server()
        
        # Register workers
        planner_info = {'name': 'Planner', 'worker_type': 'planner'}
        executor_info = {'name': 'Executor', 'worker_type': 'executor'}
        
        self.server.register_worker('planner_001', planner_info)
        self.server.register_worker('executor_001', executor_info)
        
        # Get message router and set up subscription
        registry = self.server.get_worker_registry()
        message_router = self.server._message_router
        
        # Track received messages
        received_messages = []
        
        def message_callback(message):
            received_messages.append(message)
        
        # Subscribe executor to messages
        subscription_id = message_router.subscribe_to_messages('executor_001', message_callback)
        self.assertIsNotNone(subscription_id)
        
        # Send message from planner to executor
        task_message = {
            'message_type': MessageType.TASK_DELEGATION.value,
            'content': 'Execute this task',
            'priority': MessagePriority.NORMAL.value
        }
        
        success = self.server.route_message('planner_001', 'executor_001', task_message)
        self.assertTrue(success)
        
        # Process pending messages
        processed_count = message_router.process_pending_messages()
        self.assertGreater(processed_count, 0)
        
        # Verify message was received
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].from_worker_id, 'planner_001')
        self.assertEqual(received_messages[0].to_worker_id, 'executor_001')
        
        # Test message history
        history = message_router.get_message_history('executor_001')
        self.assertEqual(len(history), 1)
        
        # Stop server
        self.server.stop_server()
    
    def test_server_error_handling_and_recovery(self):
        """Test server error handling and recovery scenarios"""
        # Test starting server twice
        self.server.start_server()
        
        with self.assertRaises(WorkerError) as context:
            self.server.start_server()
        
        self.assertIn("Cannot start server in state: running", str(context.exception))
        
        # Test operations when server is running
        worker_info = {'name': 'TestWorker', 'worker_type': 'executor'}
        reg_id = self.server.register_worker('worker_001', worker_info)
        self.assertIsNotNone(reg_id)
        
        # Stop server
        self.server.stop_server()
        
        # Test operations when server is stopped
        with self.assertRaises(WorkerError) as context:
            self.server.register_worker('worker_002', worker_info)
        
        self.assertIn("Cannot register worker - server not running", str(context.exception))
        
        with self.assertRaises(WorkerError) as context:
            self.server.route_message('worker_001', 'worker_002', {'content': 'test'})
        
        self.assertIn("Cannot route message - server not running", str(context.exception))
    
    def test_concurrent_operations(self):
        """Test concurrent server operations"""
        # Start server
        self.server.start_server()
        
        # Track results from concurrent operations
        results = {'registrations': [], 'messages': []}
        errors = []
        
        def register_workers():
            """Register workers concurrently"""
            try:
                for i in range(5):
                    worker_info = {
                        'name': f'ConcurrentWorker{i}',
                        'worker_type': 'executor',
                        'capabilities': ['testing']
                    }
                    reg_id = self.server.register_worker(f'concurrent_{i:03d}', worker_info)
                    results['registrations'].append(reg_id)
            except Exception as e:
                errors.append(e)
        
        def send_messages():
            """Send messages concurrently"""
            try:
                # Wait a bit for workers to be registered
                time.sleep(0.1)
                
                for i in range(3):
                    message = {
                        'message_type': MessageType.STATUS_UPDATE.value,
                        'content': f'Status update {i}'
                    }
                    success = self.server.route_message('concurrent_000', 'concurrent_001', message)
                    results['messages'].append(success)
            except Exception as e:
                errors.append(e)
        
        # Start concurrent operations
        thread1 = threading.Thread(target=register_workers)
        thread2 = threading.Thread(target=send_messages)
        
        thread1.start()
        thread2.start()
        
        # Wait for completion
        thread1.join(timeout=5)
        thread2.join(timeout=5)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Concurrent operations failed: {errors}")
        
        # Verify registrations succeeded
        self.assertEqual(len(results['registrations']), 5)
        self.assertTrue(all(reg_id is not None for reg_id in results['registrations']))
        
        # Verify some messages were sent (may not all succeed due to timing)
        self.assertGreater(len(results['messages']), 0)
        
        # Stop server
        self.server.stop_server()
    
    def test_server_maintenance_and_cleanup(self):
        """Test server maintenance and cleanup functionality"""
        # Configure server with short intervals for testing
        config = ServerConfig(
            heartbeat_interval=0.1,  # Very short for testing
            auto_cleanup=True
        )
        server = CollaborativeServer(config)
        
        try:
            # Start server
            server.start_server()
            
            # Register a worker
            worker_info = {'name': 'MaintenanceWorker', 'worker_type': 'executor'}
            server.register_worker('maintenance_001', worker_info)
            
            # Get registry and simulate inactive worker
            registry = server.get_worker_registry()
            
            # Set worker as inactive (this would normally be done by the maintenance loop)
            from datetime import datetime, timedelta
            old_time = datetime.now() - timedelta(hours=1)
            registry.worker_performance['maintenance_001']['last_active'] = old_time
            
            # Manually trigger cleanup
            cleaned_count = registry.cleanup_inactive_workers(inactive_threshold_minutes=30)
            
            # Verify cleanup occurred
            self.assertEqual(cleaned_count, 1)
            self.assertNotIn('maintenance_001', registry.worker_types)
            
            # Wait for maintenance loop to run
            time.sleep(0.2)
            
            # Verify server is still running
            self.assertEqual(server.state, ServerState.RUNNING)
            
        finally:
            # Stop server
            server.stop_server()


class TestServerComponentIntegration(unittest.TestCase):
    """Test integration between server components"""
    
    def test_registry_and_router_integration(self):
        """Test integration between worker registry and message router"""
        # Create server with components
        server = CollaborativeServer()
        server.start_server()
        
        try:
            # Register workers
            planner_info = {'name': 'IntegrationPlanner', 'worker_type': 'planner'}
            executor_info = {'name': 'IntegrationExecutor', 'worker_type': 'executor'}
            
            server.register_worker('integration_planner', planner_info)
            server.register_worker('integration_executor', executor_info)
            
            # Get components
            registry = server.get_worker_registry()
            router = server._message_router
            
            # Verify router can find workers from registry
            active_workers = registry.get_active_workers()
            self.assertEqual(len(active_workers), 2)
            
            # Test message routing uses registry for validation
            message = {
                'message_type': MessageType.COLLABORATION_INVITE.value,
                'content': 'Join collaboration'
            }
            
            # Valid workers should succeed
            success = router.route_message('integration_planner', 'integration_executor', message)
            self.assertTrue(success)
            
            # Invalid workers should fail
            with self.assertRaises(WorkerError):
                router.route_message('nonexistent_1', 'nonexistent_2', message)
            
            # Test broadcast to specific worker types
            broadcast_message = {
                'message_type': MessageType.BROADCAST.value,
                'content': 'Broadcast to executors'
            }
            
            sent_count = router.broadcast_message(
                'integration_planner',
                broadcast_message,
                target_worker_types=['executor']
            )
            
            # Should send to 1 executor
            self.assertEqual(sent_count, 1)
            
        finally:
            server.stop_server()


if __name__ == '__main__':
    unittest.main()
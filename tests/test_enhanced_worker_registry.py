"""
Unit tests for EnhancedWorkerRegistry

Tests the enhanced worker registry with specialized worker type support,
load balancing, and flowchart management capabilities.
"""

import unittest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from botted_library.core.enhanced_worker_registry import (
    EnhancedWorkerRegistry, WorkerType, WorkerCapability, 
    WorkerFlowchart, InteractionPattern
)
from botted_library.core.exceptions import WorkerError


class TestEnhancedWorkerRegistry(unittest.TestCase):
    """Test cases for EnhancedWorkerRegistry"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.registry = EnhancedWorkerRegistry()
        
        # Mock server instance
        self.mock_server = Mock()
        self.registry.server_instance = self.mock_server
    
    def tearDown(self):
        """Clean up after tests"""
        self.registry.shutdown()
    
    def test_registry_initialization(self):
        """Test registry initialization"""
        self.assertIsInstance(self.registry.worker_types, dict)
        self.assertIsInstance(self.registry.worker_capabilities, dict)
        self.assertIsInstance(self.registry.worker_performance, dict)
        self.assertIsInstance(self.registry.load_balancing_stats, dict)
        self.assertIsInstance(self.registry.flowcharts, dict)
        self.assertIsInstance(self.registry.active_flowcharts, set)
    
    def test_register_specialized_worker_success(self):
        """Test successful specialized worker registration"""
        worker_info = {
            'name': 'TestPlanner',
            'role': 'Planning Specialist',
            'worker_type': 'planner',
            'job_description': 'Creates execution strategies',
            'capabilities': ['planning', 'strategy'],
            'enhanced_capabilities': [
                {'name': 'strategy_creation', 'level': 8, 'description': 'Create strategies'},
                {'name': 'task_planning', 'level': 9, 'description': 'Plan tasks'}
            ],
            'max_concurrent_tasks': 5
        }
        
        registration_id = self.registry.register_specialized_worker('planner_001', worker_info)
        
        # Verify registration
        self.assertIsNotNone(registration_id)
        self.assertEqual(self.registry.worker_types['planner_001'], WorkerType.PLANNER)
        self.assertIn('planner_001', self.registry.worker_capabilities)
        self.assertIn('planner_001', self.registry.worker_performance)
        self.assertIn('planner_001', self.registry.load_balancing_stats)
        
        # Verify capabilities
        capabilities = self.registry.worker_capabilities['planner_001']
        self.assertEqual(len(capabilities), 2)
        self.assertEqual(capabilities[0].name, 'strategy_creation')
        self.assertEqual(capabilities[0].level, 8)
    
    def test_register_specialized_worker_invalid_type(self):
        """Test worker registration with invalid type"""
        worker_info = {
            'name': 'InvalidWorker',
            'worker_type': 'invalid_type'
        }
        
        with self.assertRaises(WorkerError) as context:
            self.registry.register_specialized_worker('invalid_001', worker_info)
        
        self.assertIn("Invalid worker type", str(context.exception))
    
    def test_find_workers_by_type_success(self):
        """Test finding workers by type"""
        # Register multiple workers of different types
        planner_info = {
            'name': 'Planner1',
            'worker_type': 'planner',
            'capabilities': ['planning']
        }
        executor_info = {
            'name': 'Executor1', 
            'worker_type': 'executor',
            'capabilities': ['execution']
        }
        
        self.registry.register_specialized_worker('planner_001', planner_info)
        self.registry.register_specialized_worker('executor_001', executor_info)
        
        # Find planners
        planners = self.registry.find_workers_by_type(WorkerType.PLANNER)
        self.assertEqual(len(planners), 1)
        self.assertEqual(planners[0]['worker_id'], 'planner_001')
        
        # Find executors
        executors = self.registry.find_workers_by_type(WorkerType.EXECUTOR)
        self.assertEqual(len(executors), 1)
        self.assertEqual(executors[0]['worker_id'], 'executor_001')
    
    def test_find_workers_by_type_available_only(self):
        """Test finding only available workers"""
        worker_info = {
            'name': 'BusyWorker',
            'worker_type': 'executor',
            'max_concurrent_tasks': 1
        }
        
        self.registry.register_specialized_worker('busy_001', worker_info)
        
        # Set worker to full capacity
        self.registry.load_balancing_stats['busy_001']['current_load'] = 1
        
        # Should not find worker when looking for available only
        available_workers = self.registry.find_workers_by_type(WorkerType.EXECUTOR, available_only=True)
        self.assertEqual(len(available_workers), 0)
        
        # Should find worker when not filtering by availability
        all_workers = self.registry.find_workers_by_type(WorkerType.EXECUTOR, available_only=False)
        self.assertEqual(len(all_workers), 1)
    
    def test_get_load_balanced_worker_success(self):
        """Test getting load balanced worker"""
        # Register two executor workers
        worker1_info = {
            'name': 'Executor1',
            'worker_type': 'executor',
            'enhanced_capabilities': [
                {'name': 'coding', 'level': 8, 'description': 'Coding tasks'}
            ]
        }
        worker2_info = {
            'name': 'Executor2', 
            'worker_type': 'executor',
            'enhanced_capabilities': [
                {'name': 'coding', 'level': 6, 'description': 'Coding tasks'}
            ]
        }
        
        self.registry.register_specialized_worker('executor_001', worker1_info)
        self.registry.register_specialized_worker('executor_002', worker2_info)
        
        # Request worker for coding task
        task_requirements = {
            'capabilities': ['coding'],
            'priority': 'high'
        }
        
        best_worker = self.registry.get_load_balanced_worker(WorkerType.EXECUTOR, task_requirements)
        
        # Should get a worker
        self.assertIsNotNone(best_worker)
        self.assertIn(best_worker['worker_id'], ['executor_001', 'executor_002'])
    
    def test_get_load_balanced_worker_no_available(self):
        """Test getting worker when none available"""
        # No workers registered
        task_requirements = {'capabilities': ['coding']}
        
        best_worker = self.registry.get_load_balanced_worker(WorkerType.EXECUTOR, task_requirements)
        
        # Should return None
        self.assertIsNone(best_worker)
    
    def test_create_worker_flowchart(self):
        """Test creating a worker flowchart"""
        objectives = "Implement user authentication system"
        created_by = "planner_001"
        
        flowchart = self.registry.create_worker_flowchart(
            objectives=objectives,
            created_by=created_by,
            planner_count=1,
            executor_count=2,
            verifier_count=1
        )
        
        # Verify flowchart creation
        self.assertIsNotNone(flowchart.flowchart_id)
        self.assertEqual(flowchart.objectives, objectives)
        self.assertEqual(flowchart.created_by, created_by)
        self.assertEqual(flowchart.planner_count, 1)
        self.assertEqual(flowchart.executor_count, 2)
        self.assertEqual(flowchart.verifier_count, 1)
        self.assertEqual(flowchart.status, "draft")
        
        # Verify flowchart is stored
        self.assertIn(flowchart.flowchart_id, self.registry.flowcharts)
    
    def test_activate_flowchart_success(self):
        """Test activating a flowchart"""
        # Create flowchart first
        flowchart = self.registry.create_worker_flowchart(
            objectives="Test objectives",
            created_by="test_user"
        )
        
        # Activate flowchart
        success = self.registry.activate_flowchart(flowchart.flowchart_id)
        
        # Verify activation
        self.assertTrue(success)
        self.assertEqual(flowchart.status, "active")
        self.assertIn(flowchart.flowchart_id, self.registry.active_flowcharts)
    
    def test_activate_flowchart_not_found(self):
        """Test activating non-existent flowchart"""
        success = self.registry.activate_flowchart("nonexistent_id")
        
        # Should fail
        self.assertFalse(success)
    
    def test_complete_task_assignment(self):
        """Test completing task assignment"""
        # Register worker first
        worker_info = {
            'name': 'TestWorker',
            'worker_type': 'executor'
        }
        self.registry.register_specialized_worker('worker_001', worker_info)
        
        # Set initial load
        self.registry.load_balancing_stats['worker_001']['current_load'] = 2
        
        # Complete task
        self.registry.complete_task_assignment('worker_001', success=True, completion_time=5.0)
        
        # Verify load reduction
        self.assertEqual(self.registry.load_balancing_stats['worker_001']['current_load'], 1)
        
        # Verify performance update
        perf = self.registry.worker_performance['worker_001']
        self.assertEqual(perf['tasks_completed'], 1)
        self.assertGreater(perf['success_rate'], 0.9)  # Should be high due to success
    
    def test_complete_task_assignment_failure(self):
        """Test completing failed task assignment"""
        # Register worker first
        worker_info = {
            'name': 'TestWorker',
            'worker_type': 'executor'
        }
        self.registry.register_specialized_worker('worker_001', worker_info)
        
        # Complete failed task
        self.registry.complete_task_assignment('worker_001', success=False, completion_time=10.0)
        
        # Verify performance update
        perf = self.registry.worker_performance['worker_001']
        self.assertEqual(perf['tasks_completed'], 1)
        # Success rate starts at 1.0, with exponential moving average: 0.9 * 1.0 + 0.1 * 0.0 = 0.9
        self.assertEqual(perf['success_rate'], 0.9)  # Should be 0.9 due to exponential moving average
    
    def test_cleanup_inactive_workers(self):
        """Test cleaning up inactive workers"""
        # Register worker
        worker_info = {
            'name': 'InactiveWorker',
            'worker_type': 'executor'
        }
        self.registry.register_specialized_worker('inactive_001', worker_info)
        
        # Set worker as inactive (old last_active time)
        old_time = datetime.now() - timedelta(hours=2)
        self.registry.worker_performance['inactive_001']['last_active'] = old_time
        
        # Cleanup with 1 minute threshold
        cleaned_count = self.registry.cleanup_inactive_workers(inactive_threshold_minutes=1)
        
        # Should have cleaned up 1 worker
        self.assertEqual(cleaned_count, 1)
        self.assertNotIn('inactive_001', self.registry.worker_types)
        self.assertNotIn('inactive_001', self.registry.worker_capabilities)
    
    def test_get_registry_statistics(self):
        """Test getting registry statistics"""
        # Register workers of different types
        planner_info = {'name': 'Planner1', 'worker_type': 'planner'}
        executor_info = {'name': 'Executor1', 'worker_type': 'executor'}
        verifier_info = {'name': 'Verifier1', 'worker_type': 'verifier'}
        
        self.registry.register_specialized_worker('planner_001', planner_info)
        self.registry.register_specialized_worker('executor_001', executor_info)
        self.registry.register_specialized_worker('verifier_001', verifier_info)
        
        # Create a flowchart
        self.registry.create_worker_flowchart("Test objectives", "test_user")
        
        # Get statistics
        stats = self.registry.get_registry_statistics()
        
        # Verify statistics structure
        self.assertIn('total_workers', stats)
        self.assertIn('workers_by_type', stats)
        self.assertIn('active_flowcharts', stats)
        self.assertIn('total_flowcharts', stats)
        self.assertIn('performance_metrics', stats)
        self.assertIn('load_balancing', stats)
        
        # Verify values
        self.assertEqual(stats['total_workers'], 3)
        self.assertEqual(stats['workers_by_type']['planner'], 1)
        self.assertEqual(stats['workers_by_type']['executor'], 1)
        self.assertEqual(stats['workers_by_type']['verifier'], 1)
        self.assertEqual(stats['total_flowcharts'], 1)
    
    def test_registry_shutdown(self):
        """Test registry shutdown"""
        # Register some workers and create data
        worker_info = {'name': 'TestWorker', 'worker_type': 'executor'}
        self.registry.register_specialized_worker('worker_001', worker_info)
        self.registry.create_worker_flowchart("Test", "user")
        
        # Shutdown
        self.registry.shutdown()
        
        # Verify cleanup
        self.assertEqual(len(self.registry.worker_types), 0)
        self.assertEqual(len(self.registry.worker_capabilities), 0)
        self.assertEqual(len(self.registry.worker_performance), 0)
        self.assertEqual(len(self.registry.load_balancing_stats), 0)
        self.assertEqual(len(self.registry.flowcharts), 0)
        self.assertEqual(len(self.registry.active_flowcharts), 0)


class TestWorkerCapability(unittest.TestCase):
    """Test cases for WorkerCapability dataclass"""
    
    def test_capability_creation(self):
        """Test creating a worker capability"""
        capability = WorkerCapability(
            name="coding",
            level=8,
            description="Python coding expertise"
        )
        
        self.assertEqual(capability.name, "coding")
        self.assertEqual(capability.level, 8)
        self.assertEqual(capability.description, "Python coding expertise")
        self.assertIsNone(capability.last_used)
    
    def test_capability_with_last_used(self):
        """Test capability with last used timestamp"""
        last_used = datetime.now()
        capability = WorkerCapability(
            name="testing",
            level=7,
            description="Unit testing",
            last_used=last_used
        )
        
        self.assertEqual(capability.last_used, last_used)


class TestWorkerFlowchart(unittest.TestCase):
    """Test cases for WorkerFlowchart dataclass"""
    
    def test_flowchart_creation(self):
        """Test creating a worker flowchart"""
        created_at = datetime.now()
        flowchart = WorkerFlowchart(
            flowchart_id="test_flowchart",
            objectives="Test objectives",
            planner_count=1,
            executor_count=2,
            verifier_count=1,
            interaction_patterns=[],
            execution_order=["step1", "step2"],
            success_criteria={"completed": True},
            created_by="test_user",
            created_at=created_at
        )
        
        self.assertEqual(flowchart.flowchart_id, "test_flowchart")
        self.assertEqual(flowchart.objectives, "Test objectives")
        self.assertEqual(flowchart.planner_count, 1)
        self.assertEqual(flowchart.executor_count, 2)
        self.assertEqual(flowchart.verifier_count, 1)
        self.assertEqual(flowchart.status, "draft")
        self.assertEqual(flowchart.created_by, "test_user")
        self.assertEqual(flowchart.created_at, created_at)


class TestWorkerTypeEnum(unittest.TestCase):
    """Test cases for WorkerType enum"""
    
    def test_worker_type_values(self):
        """Test WorkerType enum values"""
        self.assertEqual(WorkerType.PLANNER.value, "planner")
        self.assertEqual(WorkerType.EXECUTOR.value, "executor")
        self.assertEqual(WorkerType.VERIFIER.value, "verifier")


if __name__ == '__main__':
    unittest.main()
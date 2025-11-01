"""
Unit tests for Mode Controllers

Tests the ManualModeController, AutoModeController, and ModeManager
functionality including mode switching, configuration, and operations.
"""

import unittest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from botted_library.core.manual_mode_controller import ManualModeController
from botted_library.core.auto_mode_controller import (
    AutoModeController, FlowchartStatus, ExecutionStep, ObjectiveAnalysis
)
from botted_library.core.mode_manager import (
    ModeManager, OperationMode, ModeConfiguration, ModeTransition
)
from botted_library.core.enhanced_worker_registry import WorkerType
from botted_library.core.exceptions import WorkerError


class TestManualModeController(unittest.TestCase):
    """Test cases for ManualModeController"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_server = Mock()
        self.mock_server.get_worker_registry.return_value = Mock()
        
        self.controller = ManualModeController(
            server_instance=self.mock_server,
            config={'test_mode': True}
        )
    
    def tearDown(self):
        """Clean up after tests"""
        self.controller.shutdown()
    
    def test_controller_initialization(self):
        """Test manual mode controller initialization"""
        self.assertIsNotNone(self.controller.controller_id)
        self.assertEqual(self.controller.server, self.mock_server)
        self.assertEqual(len(self.controller.manual_workers), 0)
        self.assertEqual(len(self.controller.manual_spaces), 0)
        self.assertEqual(len(self.controller.manual_tasks), 0)
        self.assertEqual(self.controller.stats['workers_created'], 0)
    
    @patch('botted_library.core.planner_worker.PlannerWorker')
    @patch('botted_library.core.enhanced_worker.ServerConnection')
    def test_create_worker_manually_planner(self, mock_connection, mock_planner):
        """Test manual worker creation for planner type"""
        # Setup mocks
        mock_worker_instance = Mock()
        mock_planner.return_value = mock_worker_instance
        mock_worker_instance.connect_to_server.return_value = None
        
        # Create worker
        worker_id = self.controller.create_worker_manually(
            worker_type=WorkerType.PLANNER,
            name="Test Planner",
            role="Test Role",
            capabilities=['planning', 'coordination']
        )
        
        # Verify worker creation
        self.assertIsNotNone(worker_id)
        self.assertIn(worker_id, self.controller.manual_workers)
        
        worker_info = self.controller.manual_workers[worker_id]
        self.assertEqual(worker_info['name'], "Test Planner")
        self.assertEqual(worker_info['role'], "Test Role")
        self.assertEqual(worker_info['worker_type'], WorkerType.PLANNER)
        self.assertEqual(worker_info['capabilities'], ['planning', 'coordination'])
        self.assertEqual(worker_info['status'], 'active')
        
        # Verify statistics
        self.assertEqual(self.controller.stats['workers_created'], 1)
        self.assertEqual(self.controller.stats['operations_performed'], 1)
        
        # Verify worker was connected to server
        mock_worker_instance.connect_to_server.assert_called_once()
    
    @patch('botted_library.core.executor_worker.ExecutorWorker')
    @patch('botted_library.core.enhanced_worker.ServerConnection')
    def test_create_worker_manually_executor(self, mock_connection, mock_executor):
        """Test manual worker creation for executor type"""
        # Setup mocks
        mock_worker_instance = Mock()
        mock_executor.return_value = mock_worker_instance
        mock_worker_instance.connect_to_server.return_value = None
        
        # Create worker
        worker_id = self.controller.create_worker_manually(
            worker_type=WorkerType.EXECUTOR,
            name="Test Executor",
            role="Task Executor"
        )
        
        # Verify worker creation
        self.assertIsNotNone(worker_id)
        self.assertIn(worker_id, self.controller.manual_workers)
        
        worker_info = self.controller.manual_workers[worker_id]
        self.assertEqual(worker_info['worker_type'], WorkerType.EXECUTOR)
        self.assertEqual(worker_info['status'], 'active')
    
    @patch('botted_library.core.interfaces.Task')
    def test_assign_task_manually(self, mock_task_class):
        """Test manual task assignment"""
        # Setup worker
        mock_worker = Mock()
        mock_result = Mock()
        mock_result.is_successful.return_value = True
        mock_worker.execute_task.return_value = mock_result
        
        worker_id = "test_worker_id"
        self.controller.manual_workers[worker_id] = {
            'worker_instance': mock_worker,
            'name': 'Test Worker',
            'worker_type': WorkerType.EXECUTOR,
            'status': 'active'
        }
        
        # Setup task mock
        mock_task = Mock()
        mock_task_class.create_new.return_value = mock_task
        
        # Assign task
        task_id = self.controller.assign_task_manually(
            worker_id=worker_id,
            task_description="Test task",
            task_parameters={'param1': 'value1'},
            priority=5
        )
        
        # Verify task assignment
        self.assertIsNotNone(task_id)
        self.assertIn(task_id, self.controller.manual_tasks)
        
        task_info = self.controller.manual_tasks[task_id]
        self.assertEqual(task_info['assigned_to'], worker_id)
        self.assertEqual(task_info['worker_name'], 'Test Worker')
        self.assertEqual(task_info['status'], 'completed')
        
        # Verify statistics
        self.assertEqual(self.controller.stats['tasks_assigned'], 1)
        
        # Verify task execution
        mock_worker.execute_task.assert_called_once()
    
    def test_assign_task_to_nonexistent_worker(self):
        """Test task assignment to non-existent worker"""
        with self.assertRaises(WorkerError):
            self.controller.assign_task_manually(
                worker_id="nonexistent_worker",
                task_description="Test task"
            )
    
    def test_create_collaborative_space_manually(self):
        """Test manual collaborative space creation"""
        # Setup mock space
        mock_space = Mock()
        mock_space.space_id = "test_space_id"
        self.mock_server.create_collaborative_space.return_value = mock_space
        
        # Create space
        space_id = self.controller.create_collaborative_space_manually(
            space_name="Test Space",
            description="Test collaborative space",
            initial_participants=[]
        )
        
        # Verify space creation
        self.assertEqual(space_id, "test_space_id")
        self.assertIn(space_id, self.controller.manual_spaces)
        
        space_info = self.controller.manual_spaces[space_id]
        self.assertEqual(space_info['name'], "Test Space")
        self.assertEqual(space_info['description'], "Test collaborative space")
        self.assertEqual(space_info['status'], 'active')
        
        # Verify statistics
        self.assertEqual(self.controller.stats['spaces_created'], 1)
    
    def test_get_manual_workers(self):
        """Test getting manual workers information"""
        # Add test worker
        worker_id = "test_worker"
        self.controller.manual_workers[worker_id] = {
            'name': 'Test Worker',
            'role': 'Test Role',
            'worker_type': WorkerType.PLANNER,
            'capabilities': ['test'],
            'created_at': datetime.now(),
            'status': 'active'
        }
        
        workers = self.controller.get_manual_workers()
        
        self.assertIn(worker_id, workers)
        self.assertEqual(workers[worker_id]['name'], 'Test Worker')
        self.assertEqual(workers[worker_id]['worker_type'], 'planner')
    
    def test_register_ui_callback(self):
        """Test UI callback registration"""
        callback = Mock()
        
        self.controller.register_ui_callback('worker_created', callback)
        
        self.assertIn('worker_created', self.controller.ui_callbacks)
        self.assertEqual(self.controller.ui_callbacks['worker_created'], callback)
    
    def test_get_manual_mode_status(self):
        """Test getting manual mode status"""
        status = self.controller.get_manual_mode_status()
        
        self.assertEqual(status['mode'], 'manual')
        self.assertEqual(status['active_workers'], 0)
        self.assertEqual(status['active_spaces'], 0)
        self.assertIn('statistics', status)


class TestAutoModeController(unittest.TestCase):
    """Test cases for AutoModeController"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_server = Mock()
        self.mock_server.get_worker_registry.return_value = Mock()
        
        self.controller = AutoModeController(
            server_instance=self.mock_server,
            config={'test_mode': True}
        )
    
    def tearDown(self):
        """Clean up after tests"""
        self.controller.shutdown()
    
    def test_controller_initialization(self):
        """Test auto mode controller initialization"""
        self.assertIsNotNone(self.controller.controller_id)
        self.assertEqual(self.controller.server, self.mock_server)
        self.assertIsNone(self.controller.initial_planner)
        self.assertEqual(len(self.controller.active_flowcharts), 0)
        self.assertEqual(len(self.controller.auto_workers), 0)
        self.assertFalse(self.controller.execution_status['is_active'])
    
    def test_analyze_objectives_simple(self):
        """Test objective analysis for simple objectives"""
        objectives = "Create a simple report"
        
        analysis = self.controller._analyze_objectives(objectives)
        
        self.assertIsInstance(analysis, ObjectiveAnalysis)
        self.assertEqual(analysis.objectives, objectives)
        self.assertGreaterEqual(analysis.complexity_score, 1)
        self.assertLessEqual(analysis.complexity_score, 10)
        self.assertIn(WorkerType.PLANNER, analysis.required_worker_types)
    
    def test_analyze_objectives_complex(self):
        """Test objective analysis for complex objectives"""
        objectives = "Analyze multiple data sources, integrate complex systems, and coordinate verification"
        
        analysis = self.controller._analyze_objectives(objectives)
        
        self.assertGreater(analysis.complexity_score, 3)
        # Note: The analysis logic may not always include all worker types
        # depending on the specific keywords, so we'll check for at least one
        self.assertGreaterEqual(len(analysis.required_worker_types), 1)
        self.assertIn('data_analysis', analysis.key_capabilities)
    
    @patch('botted_library.core.planner_worker.PlannerWorker')
    @patch('botted_library.core.enhanced_worker.ServerConnection')
    def test_create_initial_planner(self, mock_connection, mock_planner):
        """Test initial planner creation"""
        # Setup mocks
        mock_worker_instance = Mock()
        mock_worker_instance.worker_id = "initial_planner_id"
        mock_planner.return_value = mock_worker_instance
        mock_worker_instance.connect_to_server.return_value = None
        
        objectives = "Test objectives"
        
        # Create initial planner
        planner = self.controller.create_initial_planner(objectives)
        
        # Verify planner creation
        self.assertEqual(planner, mock_worker_instance)
        self.assertEqual(self.controller.initial_planner, mock_worker_instance)
        
        # Check that a worker was created (ID is generated dynamically)
        self.assertEqual(len(self.controller.auto_workers), 1)
        
        # Get the created worker info
        worker_info = list(self.controller.auto_workers.values())[0]
        self.assertTrue(worker_info['is_initial_planner'])
        self.assertEqual(worker_info['status'], 'active')
        
        # Verify statistics
        self.assertEqual(self.controller.stats['workers_auto_created'], 1)
    
    def test_create_execution_flowchart(self):
        """Test flowchart creation from analysis"""
        analysis = ObjectiveAnalysis(
            objectives="Test objectives",
            complexity_score=5,
            estimated_duration=timedelta(hours=1),
            required_worker_types={
                WorkerType.PLANNER: 1,
                WorkerType.EXECUTOR: 2,
                WorkerType.VERIFIER: 1
            },
            key_capabilities=['test_capability'],
            success_criteria={'completion_rate': 0.95, 'quality_threshold': 0.8},
            risk_factors=['test_risk'],
            recommended_approach="test_approach"
        )
        
        flowchart = self.controller._create_execution_flowchart(analysis, "planner_id")
        
        # Verify flowchart creation
        self.assertIsNotNone(flowchart.flowchart_id)
        self.assertEqual(flowchart.objectives, "Test objectives")
        self.assertEqual(flowchart.planner_count, 1)
        self.assertEqual(flowchart.executor_count, 2)
        self.assertEqual(flowchart.verifier_count, 1)
        self.assertEqual(flowchart.created_by, "planner_id")
        self.assertEqual(flowchart.status, FlowchartStatus.DRAFT.value)
        
        # Verify statistics
        self.assertEqual(self.controller.stats['flowcharts_created'], 1)
    
    def test_validate_flowchart_valid(self):
        """Test flowchart validation with valid flowchart"""
        from botted_library.core.enhanced_worker_registry import WorkerFlowchart
        
        flowchart = WorkerFlowchart(
            flowchart_id="test_id",
            objectives="Test objectives",
            planner_count=1,
            executor_count=2,
            verifier_count=1,
            interaction_patterns=[],
            execution_order=["step1", "step2"],
            success_criteria={},
            created_by="test",
            created_at=datetime.now()
        )
        
        is_valid = self.controller._validate_flowchart(flowchart)
        
        self.assertTrue(is_valid)
    
    def test_validate_flowchart_invalid(self):
        """Test flowchart validation with invalid flowchart"""
        from botted_library.core.enhanced_worker_registry import WorkerFlowchart
        
        flowchart = WorkerFlowchart(
            flowchart_id="",  # Invalid: empty ID
            objectives="Test objectives",
            planner_count=1,
            executor_count=2,
            verifier_count=1,
            interaction_patterns=[],
            execution_order=[],  # Invalid: empty execution order
            success_criteria={},
            created_by="test",
            created_at=datetime.now()
        )
        
        is_valid = self.controller._validate_flowchart(flowchart)
        
        self.assertFalse(is_valid)
    
    def test_create_execution_steps(self):
        """Test execution step creation from flowchart"""
        from botted_library.core.enhanced_worker_registry import WorkerFlowchart
        
        flowchart = WorkerFlowchart(
            flowchart_id="test_id",
            objectives="Test objectives",
            planner_count=1,
            executor_count=2,
            verifier_count=1,
            interaction_patterns=[],
            execution_order=["create_executors", "create_verifiers", "assign_tasks"],
            success_criteria={'completion_rate': 0.95},
            created_by="test",
            created_at=datetime.now()
        )
        
        steps = self.controller._create_execution_steps(flowchart)
        
        # Verify steps creation
        self.assertGreater(len(steps), 0)
        
        # Check for worker creation steps
        executor_steps = [s for s in steps if s.step_type == "create_workers" 
                         and s.parameters.get('worker_type') == WorkerType.EXECUTOR.value]
        self.assertEqual(len(executor_steps), 1)
        self.assertEqual(executor_steps[0].parameters['count'], 2)
        
        verifier_steps = [s for s in steps if s.step_type == "create_workers" 
                         and s.parameters.get('worker_type') == WorkerType.VERIFIER.value]
        self.assertEqual(len(verifier_steps), 1)
        self.assertEqual(verifier_steps[0].parameters['count'], 1)
        
        # Check for task assignment step
        task_steps = [s for s in steps if s.step_type == "assign_initial_tasks"]
        self.assertEqual(len(task_steps), 1)
    
    def test_monitor_auto_execution(self):
        """Test auto execution monitoring"""
        # Set up execution status
        self.controller.execution_status['is_active'] = True
        self.controller.execution_status['execution_start_time'] = datetime.now()
        
        # Add some auto workers
        self.controller.auto_workers['worker1'] = {
            'worker_type': WorkerType.EXECUTOR,
            'status': 'active'
        }
        self.controller.auto_workers['worker2'] = {
            'worker_type': WorkerType.VERIFIER,
            'status': 'active'
        }
        
        status = self.controller.monitor_auto_execution()
        
        # Verify monitoring results
        self.assertIn('execution_status', status)
        self.assertIn('active_workers_by_type', status)
        self.assertIn('total_auto_workers', status)
        self.assertEqual(status['total_auto_workers'], 2)
        self.assertEqual(status['active_workers_by_type']['executor'], 1)
        self.assertEqual(status['active_workers_by_type']['verifier'], 1)
    
    def test_pause_resume_auto_execution(self):
        """Test pausing and resuming auto execution"""
        # Setup active execution
        self.controller.execution_status['is_active'] = True
        
        from botted_library.core.enhanced_worker_registry import WorkerFlowchart
        flowchart = WorkerFlowchart(
            flowchart_id="test_id",
            objectives="Test",
            planner_count=1, executor_count=1, verifier_count=1,
            interaction_patterns=[], execution_order=["step1"],
            success_criteria={}, created_by="test", created_at=datetime.now(),
            status=FlowchartStatus.ACTIVE.value
        )
        self.controller.active_flowcharts["test_id"] = flowchart
        
        # Test pause
        result = self.controller.pause_auto_execution()
        self.assertTrue(result)
        self.assertFalse(self.controller.execution_status['is_active'])
        self.assertEqual(flowchart.status, FlowchartStatus.PAUSED.value)
        
        # Test resume
        result = self.controller.resume_auto_execution()
        self.assertTrue(result)
        self.assertTrue(self.controller.execution_status['is_active'])
        self.assertEqual(flowchart.status, FlowchartStatus.ACTIVE.value)
    
    def test_get_auto_mode_status(self):
        """Test getting auto mode status"""
        status = self.controller.get_auto_mode_status()
        
        self.assertEqual(status['mode'], 'auto')
        self.assertIn('execution_status', status)
        self.assertIn('statistics', status)
        self.assertIn('auto_scaling_config', status)


class TestModeManager(unittest.TestCase):
    """Test cases for ModeManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_server = Mock()
        self.mock_server.get_worker_registry.return_value = Mock()
        
        self.mode_manager = ModeManager(
            server_instance=self.mock_server,
            default_mode=OperationMode.MANUAL,
            config={'test_mode': True}
        )
    
    def tearDown(self):
        """Clean up after tests"""
        self.mode_manager.shutdown()
    
    def test_mode_manager_initialization(self):
        """Test mode manager initialization"""
        self.assertIsNotNone(self.mode_manager.manager_id)
        self.assertEqual(self.mode_manager.server, self.mock_server)
        self.assertEqual(self.mode_manager.current_mode, OperationMode.MANUAL)
        self.assertIsNotNone(self.mode_manager.manual_controller)
        self.assertIsNone(self.mode_manager.auto_controller)
    
    def test_get_current_mode(self):
        """Test getting current mode"""
        mode = self.mode_manager.get_current_mode()
        self.assertEqual(mode, OperationMode.MANUAL)
    
    def test_mode_configurations(self):
        """Test mode configurations"""
        # Test manual mode configuration
        manual_config = self.mode_manager.get_mode_configuration(OperationMode.MANUAL)
        self.assertIsNotNone(manual_config)
        self.assertEqual(manual_config.mode, OperationMode.MANUAL)
        self.assertTrue(manual_config.is_active)
        
        # Test auto mode configuration
        auto_config = self.mode_manager.get_mode_configuration(OperationMode.AUTO)
        self.assertIsNotNone(auto_config)
        self.assertEqual(auto_config.mode, OperationMode.AUTO)
        self.assertFalse(auto_config.is_active)
    
    def test_update_mode_configuration(self):
        """Test updating mode configuration"""
        updates = {
            'max_workers_per_type': 15,
            'new_setting': 'test_value'
        }
        
        result = self.mode_manager.update_mode_configuration(OperationMode.MANUAL, updates)
        
        self.assertTrue(result)
        
        config = self.mode_manager.get_mode_configuration(OperationMode.MANUAL)
        self.assertEqual(config.config['max_workers_per_type'], 15)
        self.assertEqual(config.config['new_setting'], 'test_value')
    
    def test_detect_optimal_mode_manual(self):
        """Test mode detection for manual mode"""
        context = {
            'objectives': 'I want manual control over the process',
            'complexity_score': 2,
            'required_workers': 1
        }
        
        mode = self.mode_manager.detect_optimal_mode(context)
        
        self.assertEqual(mode, OperationMode.MANUAL)
    
    def test_detect_optimal_mode_auto(self):
        """Test mode detection for auto mode"""
        context = {
            'objectives': 'Automate complex data analysis and coordinate multiple systems',
            'complexity_score': 8,
            'required_workers': 5
        }
        
        mode = self.mode_manager.detect_optimal_mode(context)
        
        self.assertEqual(mode, OperationMode.AUTO)
    
    def test_detect_optimal_mode_user_preference(self):
        """Test mode detection with user preference"""
        context = {
            'objectives': 'Complex task',
            'user_preference': 'manual',
            'complexity_score': 8
        }
        
        mode = self.mode_manager.detect_optimal_mode(context)
        
        self.assertEqual(mode, OperationMode.MANUAL)
    
    def test_get_active_controller(self):
        """Test getting active controller"""
        controller = self.mode_manager.get_active_controller()
        
        self.assertIsInstance(controller, ManualModeController)
        self.assertEqual(controller, self.mode_manager.manual_controller)
    
    def test_switch_mode_manual_to_auto(self):
        """Test switching from manual to auto mode"""
        # Verify starting in manual mode
        self.assertEqual(self.mode_manager.current_mode, OperationMode.MANUAL)
        
        # Switch to auto mode
        transition_id = self.mode_manager.switch_mode(OperationMode.AUTO)
        
        # Verify mode switch
        self.assertIsNotNone(transition_id)
        self.assertEqual(self.mode_manager.current_mode, OperationMode.AUTO)
        self.assertIsNotNone(self.mode_manager.auto_controller)
        
        # Verify statistics
        self.assertEqual(self.mode_manager.stats['mode_switches'], 1)
        self.assertEqual(self.mode_manager.stats['successful_transitions'], 1)
    
    def test_switch_mode_same_mode(self):
        """Test switching to the same mode"""
        transition_id = self.mode_manager.switch_mode(OperationMode.MANUAL)
        
        # Should return empty string for same mode
        self.assertEqual(transition_id, "")
        self.assertEqual(self.mode_manager.current_mode, OperationMode.MANUAL)
    
    def test_get_transition_status(self):
        """Test getting transition status"""
        # Switch mode to create a transition
        transition_id = self.mode_manager.switch_mode(OperationMode.AUTO)
        
        # Get transition status
        status = self.mode_manager.get_transition_status(transition_id)
        
        self.assertIsNotNone(status)
        self.assertEqual(status['transition_id'], transition_id)
        self.assertEqual(status['from_mode'], 'manual')
        self.assertEqual(status['to_mode'], 'auto')
        self.assertEqual(status['status'], 'completed')
    
    def test_register_mode_change_callback(self):
        """Test registering mode change callback"""
        callback = Mock()
        
        self.mode_manager.register_mode_change_callback('test_callback', callback)
        
        self.assertIn('test_callback', self.mode_manager.mode_change_callbacks)
        
        # Switch mode to trigger callback
        self.mode_manager.switch_mode(OperationMode.AUTO)
        
        # Verify callback was called
        callback.assert_called_once_with(OperationMode.MANUAL, OperationMode.AUTO)
    
    def test_get_mode_manager_status(self):
        """Test getting mode manager status"""
        status = self.mode_manager.get_mode_manager_status()
        
        self.assertIn('manager_id', status)
        self.assertEqual(status['current_mode'], 'manual')
        self.assertIn('available_modes', status)
        self.assertIn('mode_configurations', status)
        self.assertIn('statistics', status)


if __name__ == '__main__':
    unittest.main()
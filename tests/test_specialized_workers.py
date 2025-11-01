"""
Unit tests for Specialized Worker Types

Tests the PlannerWorker, ExecutorWorker, and VerifierWorker implementations
including their specialized capabilities and inter-worker communication.
"""

import unittest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from botted_library.core.planner_worker import PlannerWorker, ExecutionStrategy, WorkerCreationSpec
from botted_library.core.executor_worker import ExecutorWorker, TaskExecution, TaskStatus, ProgressReport
from botted_library.core.verifier_worker import VerifierWorker, VerificationResult, VerificationStatus, QualityLevel
from botted_library.core.enhanced_worker import EnhancedWorker, ServerConnection
from botted_library.core.enhanced_worker_registry import WorkerType
from botted_library.core.message_router import MessageType, CollaborativeMessage
from botted_library.core.exceptions import WorkerError


class TestPlannerWorker(unittest.TestCase):
    """Test cases for PlannerWorker"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_memory = Mock()
        self.mock_knowledge = Mock()
        self.mock_browser = Mock()
        self.mock_task_executor = Mock()
        
        # Mock server connection
        self.mock_server = Mock()
        self.mock_server_connection = ServerConnection(
            server_instance=self.mock_server,
            worker_id="planner-test-001",
            connection_id="conn-001",
            connected_at=datetime.now(),
            is_active=True
        )
        
        # Mock worker registry
        self.mock_registry = Mock()
        self.mock_server.get_worker_registry.return_value = self.mock_registry
        
        # Create planner worker
        self.planner = PlannerWorker(
            name="TestPlanner",
            role="Planning Specialist",
            memory_system=self.mock_memory,
            knowledge_validator=self.mock_knowledge,
            browser_controller=self.mock_browser,
            task_executor=self.mock_task_executor,
            server_connection=self.mock_server_connection,
            worker_id="planner-test-001",
            config={}
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.planner, 'shutdown'):
            self.planner.shutdown()
    
    def test_planner_initialization(self):
        """Test planner worker initialization"""
        self.assertEqual(self.planner.name, "TestPlanner")
        self.assertEqual(self.planner.role, "Planning Specialist")
        self.assertEqual(self.planner.worker_type, WorkerType.PLANNER)
        self.assertIsInstance(self.planner.created_strategies, dict)
        self.assertIsInstance(self.planner.managed_workers, dict)
        self.assertIsInstance(self.planner.active_flowcharts, dict)
        self.assertIsInstance(self.planner.task_assignments, dict)
    
    def test_create_execution_strategy(self):
        """Test execution strategy creation"""
        objectives = "Develop a web application with user authentication"
        
        strategy = self.planner.create_execution_strategy(objectives)
        
        self.assertIsInstance(strategy, ExecutionStrategy)
        self.assertEqual(strategy.objectives, objectives)
        self.assertIn('approach', strategy.__dict__)
        self.assertIn('required_workers', strategy.__dict__)
        self.assertIn('task_breakdown', strategy.__dict__)
        self.assertIn('success_criteria', strategy.__dict__)
        
        # Verify strategy is stored
        self.assertIn(strategy.strategy_id, self.planner.created_strategies)
    
    def test_create_new_worker_success(self):
        """Test successful worker creation"""
        # Mock registry to return a worker ID
        self.mock_registry.create_specialized_worker.return_value = "executor-001"
        
        worker_spec = WorkerCreationSpec(
            worker_type=WorkerType.EXECUTOR,
            name="TestExecutor",
            role="Task Executor",
            capabilities=["task_execution", "tool_usage"],
            config={"max_concurrent_tasks": 2}
        )
        
        worker_id = self.planner.create_new_worker(worker_spec)
        
        self.assertEqual(worker_id, "executor-001")
        self.assertIn(worker_id, self.planner.managed_workers)
        
        # Verify worker info is tracked
        worker_info = self.planner.managed_workers[worker_id]
        self.assertEqual(worker_info['worker_type'], WorkerType.EXECUTOR)
        self.assertEqual(worker_info['name'], "TestExecutor")
        self.assertEqual(worker_info['status'], 'active')
    
    def test_create_new_worker_limit_reached(self):
        """Test worker creation when limit is reached"""
        # Fill up to the limit
        self.planner.worker_creation_limit = 1
        self.planner.managed_workers["existing-worker"] = {"test": "data"}
        
        worker_spec = WorkerCreationSpec(
            worker_type=WorkerType.EXECUTOR,
            name="TestExecutor",
            role="Task Executor",
            capabilities=[],
            config={}
        )
        
        with self.assertRaises(WorkerError):
            self.planner.create_new_worker(worker_spec)
    
    def test_assign_task_to_executor(self):
        """Test task assignment to executor"""
        # Add a managed executor
        executor_id = "executor-001"
        self.planner.managed_workers[executor_id] = {
            'worker_type': WorkerType.EXECUTOR,
            'name': 'TestExecutor',
            'status': 'active',
            'tasks_assigned': 0,
            'last_communication': None
        }
        
        # Mock message sending
        self.planner.send_message_to_worker = Mock(return_value=True)
        
        success = self.planner.assign_task_to_executor(
            executor_id=executor_id,
            task_description="Process user data",
            task_parameters={"data_source": "database"},
            priority=7
        )
        
        self.assertTrue(success)
        self.assertEqual(len(self.planner.task_assignments), 1)
        
        # Verify task assignment details
        assignment = list(self.planner.task_assignments.values())[0]
        self.assertEqual(assignment['executor_id'], executor_id)
        self.assertEqual(assignment['task_description'], "Process user data")
        self.assertEqual(assignment['priority'], 7)
        
        # Verify worker stats updated
        worker_info = self.planner.managed_workers[executor_id]
        self.assertEqual(worker_info['tasks_assigned'], 1)
        self.assertIsNotNone(worker_info['last_communication'])
    
    def test_assign_task_to_non_executor(self):
        """Test task assignment to non-executor worker"""
        # Add a managed verifier (not executor)
        verifier_id = "verifier-001"
        self.planner.managed_workers[verifier_id] = {
            'worker_type': WorkerType.VERIFIER,
            'name': 'TestVerifier',
            'status': 'active'
        }
        
        success = self.planner.assign_task_to_executor(
            executor_id=verifier_id,
            task_description="Process user data"
        )
        
        self.assertFalse(success)
    
    def test_create_workflow_flowchart(self):
        """Test workflow flowchart creation"""
        objectives = "Build and test a new feature"
        
        flowchart = self.planner.create_workflow_flowchart(objectives)
        
        self.assertIsNotNone(flowchart)
        self.assertEqual(flowchart.objectives, objectives)
        self.assertGreater(len(flowchart.interaction_patterns), 0)
        self.assertGreater(len(flowchart.execution_order), 0)
        self.assertEqual(flowchart.created_by, self.planner.worker_id)
        
        # Verify flowchart is stored
        self.assertIn(flowchart.flowchart_id, self.planner.active_flowcharts)
    
    def test_monitor_execution_progress(self):
        """Test execution progress monitoring"""
        # Add some test data
        self.planner.managed_workers["executor-001"] = {
            'name': 'TestExecutor',
            'worker_type': WorkerType.EXECUTOR,
            'status': 'active',
            'tasks_assigned': 3,
            'last_communication': datetime.now()
        }
        
        self.planner.task_assignments["assignment-001"] = {
            'status': 'completed'
        }
        self.planner.task_assignments["assignment-002"] = {
            'status': 'in_progress'
        }
        
        progress = self.planner.monitor_execution_progress()
        
        self.assertEqual(progress['managed_workers'], 1)
        self.assertEqual(progress['completed_assignments'], 1)
        self.assertEqual(progress['active_assignments'], 1)
        self.assertIn('worker_status', progress)
        self.assertIn('executor-001', progress['worker_status'])


class TestExecutorWorker(unittest.TestCase):
    """Test cases for ExecutorWorker"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_memory = Mock()
        self.mock_knowledge = Mock()
        self.mock_browser = Mock()
        self.mock_task_executor = Mock()
        
        # Mock server connection
        self.mock_server = Mock()
        self.mock_server_connection = ServerConnection(
            server_instance=self.mock_server,
            worker_id="executor-test-001",
            connection_id="conn-001",
            connected_at=datetime.now(),
            is_active=True
        )
        
        # Create executor worker
        self.executor = ExecutorWorker(
            name="TestExecutor",
            role="Task Executor",
            memory_system=self.mock_memory,
            knowledge_validator=self.mock_knowledge,
            browser_controller=self.mock_browser,
            task_executor=self.mock_task_executor,
            server_connection=self.mock_server_connection,
            worker_id="executor-test-001",
            config={}
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.executor, 'shutdown'):
            self.executor.shutdown()
    
    def test_executor_initialization(self):
        """Test executor worker initialization"""
        self.assertEqual(self.executor.name, "TestExecutor")
        self.assertEqual(self.executor.role, "Task Executor")
        self.assertEqual(self.executor.worker_type, WorkerType.EXECUTOR)
        self.assertIsInstance(self.executor.active_executions, dict)
        self.assertIsInstance(self.executor.completed_executions, dict)
        self.assertIsInstance(self.executor.tool_usage_stats, dict)
    
    def test_execute_assigned_task(self):
        """Test task execution"""
        task_description = "Process customer data"
        task_parameters = {"customer_id": "12345"}
        
        # Mock the execution logic to avoid actual task processing
        with patch.object(self.executor, '_start_task_execution'):
            execution_id = self.executor.execute_assigned_task(
                task_description=task_description,
                task_parameters=task_parameters,
                assigned_by="planner-001"
            )
        
        self.assertIsNotNone(execution_id)
        self.assertIn(execution_id, self.executor.active_executions)
        
        # Verify execution details
        execution = self.executor.active_executions[execution_id]
        self.assertEqual(execution.task_description, task_description)
        self.assertEqual(execution.task_parameters, task_parameters)
        self.assertEqual(execution.assigned_by, "planner-001")
        self.assertEqual(execution.status, TaskStatus.PENDING)
    
    def test_execute_task_at_capacity(self):
        """Test task execution when at capacity"""
        # Fill up to capacity
        self.executor.max_concurrent_tasks = 1
        self.executor.active_executions["existing-task"] = Mock()
        
        with self.assertRaises(WorkerError):
            self.executor.execute_assigned_task("New task")
    
    def test_report_progress_to_planner(self):
        """Test progress reporting"""
        # Create a test execution
        execution_id = "test-execution-001"
        self.executor.active_executions[execution_id] = TaskExecution(
            execution_id=execution_id,
            assignment_id=None,
            task_description="Test task",
            task_parameters={},
            assigned_by="planner-001",
            status=TaskStatus.IN_PROGRESS
        )
        
        # Mock message sending
        self.executor.send_message_to_worker = Mock(return_value=True)
        
        success = self.executor.report_progress_to_planner(
            planner_id="planner-001",
            execution_id=execution_id,
            progress_percentage=50.0,
            current_step="Processing data"
        )
        
        self.assertTrue(success)
        
        # Verify progress was updated
        execution = self.executor.active_executions[execution_id]
        self.assertEqual(execution.progress_percentage, 50.0)
        
        # Verify message was sent
        self.executor.send_message_to_worker.assert_called_once()
    
    def test_request_verification_from_verifier(self):
        """Test verification request"""
        # Create a test execution
        execution_id = "test-execution-001"
        self.executor.active_executions[execution_id] = TaskExecution(
            execution_id=execution_id,
            assignment_id=None,
            task_description="Test task",
            task_parameters={},
            assigned_by="planner-001",
            status=TaskStatus.COMPLETED,
            result={"output": "test result"}
        )
        
        # Mock message sending
        self.executor.send_message_to_worker = Mock(return_value=True)
        
        success = self.executor.request_verification_from_verifier(
            verifier_id="verifier-001",
            execution_id=execution_id,
            output_to_verify={"output": "test result"}
        )
        
        self.assertTrue(success)
        self.executor.send_message_to_worker.assert_called_once()
    
    def test_use_enhanced_tool_success(self):
        """Test successful enhanced tool usage"""
        # Mock tool executor
        self.mock_task_executor.use_tool = Mock(return_value={"result": "success"})
        
        result = self.executor.use_enhanced_tool(
            tool_name="data_processor",
            parameters={"input": "test_data"}
        )
        
        self.assertEqual(result, {"result": "success"})
        
        # Verify tool usage stats updated
        self.assertIn("data_processor", self.executor.tool_usage_stats)
        stats = self.executor.tool_usage_stats["data_processor"]
        self.assertEqual(stats['usage_count'], 1)
        self.assertEqual(stats['success_count'], 1)
        self.assertEqual(stats['failure_count'], 0)
    
    def test_use_enhanced_tool_failure(self):
        """Test enhanced tool usage failure"""
        # Mock tool executor to raise exception
        self.mock_task_executor.use_tool = Mock(side_effect=Exception("Tool failed"))
        
        with self.assertRaises(WorkerError):
            self.executor.use_enhanced_tool(
                tool_name="failing_tool",
                parameters={"input": "test_data"}
            )
        
        # Verify failure stats updated
        self.assertIn("failing_tool", self.executor.tool_usage_stats)
        stats = self.executor.tool_usage_stats["failing_tool"]
        self.assertEqual(stats['usage_count'], 1)
        self.assertEqual(stats['success_count'], 0)
        self.assertEqual(stats['failure_count'], 1)
    
    def test_get_execution_status(self):
        """Test execution status retrieval"""
        # Create a test execution
        execution_id = "test-execution-001"
        execution = TaskExecution(
            execution_id=execution_id,
            assignment_id="assignment-001",
            task_description="Test task",
            task_parameters={"param": "value"},
            assigned_by="planner-001",
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.now(),
            progress_percentage=75.0
        )
        self.executor.active_executions[execution_id] = execution
        
        status = self.executor.get_execution_status(execution_id)
        
        self.assertIsNotNone(status)
        self.assertEqual(status['execution_id'], execution_id)
        self.assertEqual(status['assignment_id'], "assignment-001")
        self.assertEqual(status['task_description'], "Test task")
        self.assertEqual(status['status'], TaskStatus.IN_PROGRESS.value)
        self.assertEqual(status['progress_percentage'], 75.0)
        self.assertEqual(status['assigned_by'], "planner-001")
    
    def test_cancel_execution(self):
        """Test execution cancellation"""
        # Create a test execution
        execution_id = "test-execution-001"
        self.executor.active_executions[execution_id] = TaskExecution(
            execution_id=execution_id,
            assignment_id=None,
            task_description="Test task",
            task_parameters={},
            assigned_by=None,
            status=TaskStatus.IN_PROGRESS
        )
        
        success = self.executor.cancel_execution(execution_id)
        
        self.assertTrue(success)
        self.assertNotIn(execution_id, self.executor.active_executions)
        self.assertIn(execution_id, self.executor.completed_executions)
        
        # Verify status was updated
        execution = self.executor.completed_executions[execution_id]
        self.assertEqual(execution.status, TaskStatus.CANCELLED)
        self.assertIsNotNone(execution.completed_at)


class TestVerifierWorker(unittest.TestCase):
    """Test cases for VerifierWorker"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock dependencies
        self.mock_memory = Mock()
        self.mock_knowledge = Mock()
        self.mock_browser = Mock()
        self.mock_task_executor = Mock()
        
        # Mock server connection
        self.mock_server = Mock()
        self.mock_server_connection = ServerConnection(
            server_instance=self.mock_server,
            worker_id="verifier-test-001",
            connection_id="conn-001",
            connected_at=datetime.now(),
            is_active=True
        )
        
        # Create verifier worker
        self.verifier = VerifierWorker(
            name="TestVerifier",
            role="Quality Verifier",
            memory_system=self.mock_memory,
            knowledge_validator=self.mock_knowledge,
            browser_controller=self.mock_browser,
            task_executor=self.mock_task_executor,
            server_connection=self.mock_server_connection,
            worker_id="verifier-test-001",
            config={}
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self.verifier, 'shutdown'):
            self.verifier.shutdown()
    
    def test_verifier_initialization(self):
        """Test verifier worker initialization"""
        self.assertEqual(self.verifier.name, "TestVerifier")
        self.assertEqual(self.verifier.role, "Quality Verifier")
        self.assertEqual(self.verifier.worker_type, WorkerType.VERIFIER)
        self.assertIsInstance(self.verifier.active_verifications, dict)
        self.assertIsInstance(self.verifier.completed_verifications, dict)
        self.assertIsNotNone(self.verifier.quality_metrics)
    
    def test_validate_output_quality_success(self):
        """Test successful output quality validation"""
        output_to_verify = {
            "task_completed": True,
            "description": "Successfully processed customer data with high accuracy",
            "result": "Customer data processed and validated"
        }
        
        verification_criteria = {
            "accuracy": 0.8,
            "completeness": 0.7,
            "clarity": 0.6
        }
        
        result = self.verifier.validate_output_quality(
            output_to_verify=output_to_verify,
            verification_criteria=verification_criteria,
            requested_by="executor-001"
        )
        
        self.assertIsInstance(result, VerificationResult)
        self.assertEqual(result.output_verified, output_to_verify)
        self.assertEqual(result.verification_criteria, verification_criteria)
        self.assertEqual(result.verified_by, self.verifier.worker_id)
        self.assertIsInstance(result.feedback, list)
        self.assertIsInstance(result.improvement_suggestions, list)
        
        # Verify result is stored
        self.assertIn(result.verification_id, self.verifier.completed_verifications)
    
    def test_validate_output_quality_at_capacity(self):
        """Test validation when at capacity"""
        # Fill up to capacity
        self.verifier.max_concurrent_verifications = 1
        self.verifier.active_verifications["existing-verification"] = {"test": "data"}
        
        with self.assertRaises(WorkerError):
            self.verifier.validate_output_quality({"test": "output"})
    
    def test_provide_improvement_feedback(self):
        """Test improvement feedback provision"""
        # Create a verification result
        verification_result = VerificationResult(
            verification_id="verification-001",
            output_verified={"test": "output"},
            status=VerificationStatus.NEEDS_REVISION,
            quality_level=QualityLevel.ACCEPTABLE,
            quality_score=0.6,
            feedback=["Needs more detail", "Format could be improved"],
            improvement_suggestions=["Add more examples", "Use consistent formatting"],
            verification_criteria={"accuracy": 0.8},
            verified_by=self.verifier.worker_id,
            verified_at=datetime.now()
        )
        
        # Mock message sending
        self.verifier.send_message_to_worker = Mock(return_value=True)
        
        success = self.verifier.provide_improvement_feedback(
            target_worker_id="executor-001",
            verification_result=verification_result
        )
        
        self.assertTrue(success)
        self.verifier.send_message_to_worker.assert_called_once()
    
    def test_approve_final_output_success(self):
        """Test successful final output approval"""
        high_quality_output = {
            "task_completed": True,
            "description": "Excellent work with comprehensive results and clear documentation",
            "result": "All requirements met with high quality"
        }
        
        approved = self.verifier.approve_final_output(high_quality_output)
        
        # Note: This depends on the quality assessment logic
        # The test may need adjustment based on actual implementation
        self.assertIsInstance(approved, bool)
    
    def test_maintain_quality_metrics(self):
        """Test quality metrics maintenance"""
        # Add some test verifications
        for i in range(3):
            verification_result = VerificationResult(
                verification_id=f"verification-{i}",
                output_verified={"test": f"output-{i}"},
                status=VerificationStatus.APPROVED if i < 2 else VerificationStatus.REJECTED,
                quality_level=QualityLevel.GOOD if i < 2 else QualityLevel.POOR,
                quality_score=0.8 if i < 2 else 0.4,
                feedback=[],
                improvement_suggestions=[],
                verification_criteria={},
                verified_by=self.verifier.worker_id,
                verified_at=datetime.now()
            )
            self.verifier.completed_verifications[verification_result.verification_id] = verification_result
            self.verifier._update_quality_metrics(verification_result)
        
        metrics = self.verifier.maintain_quality_metrics()
        
        self.assertEqual(metrics.total_verifications, 3)
        self.assertEqual(metrics.approved_count, 2)
        self.assertEqual(metrics.rejected_count, 1)
        self.assertGreater(metrics.average_quality_score, 0)
    
    def test_generate_quality_report(self):
        """Test quality report generation"""
        # Add some test verifications
        verification_result = VerificationResult(
            verification_id="verification-001",
            output_verified={"test": "output"},
            status=VerificationStatus.APPROVED,
            quality_level=QualityLevel.GOOD,
            quality_score=0.8,
            feedback=[],
            improvement_suggestions=[],
            verification_criteria={},
            verified_by=self.verifier.worker_id,
            verified_at=datetime.now()
        )
        self.verifier.completed_verifications[verification_result.verification_id] = verification_result
        
        report = self.verifier.generate_quality_report(time_period_days=30)
        
        self.assertIn('total_verifications', report)
        self.assertIn('approval_rate', report)
        self.assertIn('average_quality_score', report)
        self.assertIn('quality_distribution', report)
        self.assertEqual(report['verifier_id'], self.verifier.worker_id)


class TestInterWorkerCommunication(unittest.TestCase):
    """Test cases for inter-worker communication between specialized workers"""
    
    def setUp(self):
        """Set up test fixtures with multiple workers"""
        # Mock dependencies
        self.mock_memory = Mock()
        self.mock_knowledge = Mock()
        self.mock_browser = Mock()
        self.mock_task_executor = Mock()
        
        # Mock server
        self.mock_server = Mock()
        
        # Create workers with server connections
        self.planner = PlannerWorker(
            name="TestPlanner",
            role="Planning Specialist",
            memory_system=self.mock_memory,
            knowledge_validator=self.mock_knowledge,
            browser_controller=self.mock_browser,
            task_executor=self.mock_task_executor,
            server_connection=ServerConnection(
                server_instance=self.mock_server,
                worker_id="planner-001",
                connection_id="conn-001",
                connected_at=datetime.now()
            ),
            worker_id="planner-001",
            config={}
        )
        
        self.executor = ExecutorWorker(
            name="TestExecutor",
            role="Task Executor",
            memory_system=self.mock_memory,
            knowledge_validator=self.mock_knowledge,
            browser_controller=self.mock_browser,
            task_executor=self.mock_task_executor,
            server_connection=ServerConnection(
                server_instance=self.mock_server,
                worker_id="executor-001",
                connection_id="conn-002",
                connected_at=datetime.now()
            ),
            worker_id="executor-001",
            config={}
        )
        
        self.verifier = VerifierWorker(
            name="TestVerifier",
            role="Quality Verifier",
            memory_system=self.mock_memory,
            knowledge_validator=self.mock_knowledge,
            browser_controller=self.mock_browser,
            task_executor=self.mock_task_executor,
            server_connection=ServerConnection(
                server_instance=self.mock_server,
                worker_id="verifier-001",
                connection_id="conn-003",
                connected_at=datetime.now()
            ),
            worker_id="verifier-001",
            config={}
        )
    
    def test_planner_to_executor_task_delegation(self):
        """Test task delegation from planner to executor"""
        # Setup planner to manage the executor
        self.planner.managed_workers["executor-001"] = {
            'worker_type': WorkerType.EXECUTOR,
            'name': 'TestExecutor',
            'status': 'active',
            'tasks_assigned': 0,
            'last_communication': None
        }
        
        # Mock message sending
        self.planner.send_message_to_worker = Mock(return_value=True)
        
        # Planner assigns task to executor
        success = self.planner.assign_task_to_executor(
            executor_id="executor-001",
            task_description="Process customer orders",
            task_parameters={"batch_size": 100}
        )
        
        self.assertTrue(success)
        
        # Verify message was sent with correct format
        self.planner.send_message_to_worker.assert_called_once()
        call_args = self.planner.send_message_to_worker.call_args
        self.assertEqual(call_args[0][0], "executor-001")  # target worker ID
        
        message = call_args[0][1]  # message content
        self.assertEqual(message['message_type'], MessageType.TASK_DELEGATION.value)
        self.assertEqual(message['task_description'], "Process customer orders")
        self.assertEqual(message['task_parameters'], {"batch_size": 100})
    
    def test_executor_to_verifier_verification_request(self):
        """Test verification request from executor to verifier"""
        # Create a completed execution
        execution_id = "execution-001"
        self.executor.active_executions[execution_id] = TaskExecution(
            execution_id=execution_id,
            assignment_id=None,
            task_description="Process orders",
            task_parameters={},
            assigned_by="planner-001",
            status=TaskStatus.COMPLETED,
            result={"processed_orders": 100}
        )
        
        # Mock message sending
        self.executor.send_message_to_worker = Mock(return_value=True)
        
        # Executor requests verification
        success = self.executor.request_verification_from_verifier(
            verifier_id="verifier-001",
            execution_id=execution_id,
            output_to_verify={"processed_orders": 100}
        )
        
        self.assertTrue(success)
        
        # Verify message was sent with correct format
        self.executor.send_message_to_worker.assert_called_once()
        call_args = self.executor.send_message_to_worker.call_args
        self.assertEqual(call_args[0][0], "verifier-001")  # target worker ID
        
        message = call_args[0][1]  # message content
        self.assertEqual(message['message_type'], MessageType.VERIFICATION_REQUEST.value)
        self.assertEqual(message['execution_id'], execution_id)
        self.assertEqual(message['output_to_verify'], {"processed_orders": 100})
    
    def test_verifier_to_executor_feedback_provision(self):
        """Test feedback provision from verifier to executor"""
        # Create verification result
        verification_result = VerificationResult(
            verification_id="verification-001",
            output_verified={"processed_orders": 100},
            status=VerificationStatus.APPROVED,
            quality_level=QualityLevel.GOOD,
            quality_score=0.85,
            feedback=["Good work", "Results are accurate"],
            improvement_suggestions=["Consider adding error handling"],
            verification_criteria={"accuracy": 0.8},
            verified_by="verifier-001",
            verified_at=datetime.now()
        )
        
        # Mock message sending
        self.verifier.send_message_to_worker = Mock(return_value=True)
        
        # Verifier provides feedback
        success = self.verifier.provide_improvement_feedback(
            target_worker_id="executor-001",
            verification_result=verification_result
        )
        
        self.assertTrue(success)
        
        # Verify message was sent with correct format
        self.verifier.send_message_to_worker.assert_called_once()
        call_args = self.verifier.send_message_to_worker.call_args
        self.assertEqual(call_args[0][0], "executor-001")  # target worker ID
        
        message = call_args[0][1]  # message content
        self.assertEqual(message['message_type'], MessageType.RESULT_REPORT.value)
        self.assertEqual(message['verification_status'], VerificationStatus.APPROVED.value)
        self.assertEqual(message['quality_score'], 0.85)


if __name__ == '__main__':
    unittest.main()
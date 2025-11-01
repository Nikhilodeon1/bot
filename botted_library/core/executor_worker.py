"""
Executor Worker Implementation

Specialized worker type that executes tasks, uses tools, and reports progress
to planners and verifiers in the collaborative system.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .enhanced_worker import EnhancedWorker
from .enhanced_worker_registry import WorkerType
from .message_router import MessageType
from .exceptions import WorkerError


class TaskStatus(Enum):
    """Status of task execution"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskExecution:
    """Represents a task being executed"""
    execution_id: str
    assignment_id: Optional[str]
    task_description: str
    task_parameters: Dict[str, Any]
    assigned_by: Optional[str]
    status: TaskStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error_details: Optional[Dict[str, Any]] = None
    progress_percentage: float = 0.0
    
    def __post_init__(self):
        if self.started_at is None and self.status == TaskStatus.IN_PROGRESS:
            self.started_at = datetime.now()


@dataclass
class ProgressReport:
    """Progress report for task execution"""
    execution_id: str
    progress_percentage: float
    status: TaskStatus
    current_step: str
    estimated_completion: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ExecutorWorker(EnhancedWorker):
    """
    Executor worker specialization for task execution and tool usage.
    
    Capabilities:
    - Execute assigned tasks with progress tracking
    - Use enhanced tools and integrations
    - Report progress to planners
    - Request verification from verifiers
    - Handle multiple concurrent tasks
    """
    
    def __init__(self, name: str, role: str, memory_system, knowledge_validator,
                 browser_controller, task_executor, server_connection=None,
                 worker_id=None, config=None):
        """
        Initialize executor worker.
        
        Args:
            name: Human-readable name for the executor
            role: Executor's role/title
            memory_system: Memory system instance
            knowledge_validator: Knowledge validator instance
            browser_controller: Browser controller instance
            task_executor: Task executor instance
            server_connection: Connection to collaborative server
            worker_id: Optional unique identifier
            config: Optional configuration parameters
        """
        super().__init__(
            name=name,
            role=role,
            worker_type=WorkerType.EXECUTOR,
            memory_system=memory_system,
            knowledge_validator=knowledge_validator,
            browser_controller=browser_controller,
            task_executor=task_executor,
            server_connection=server_connection,
            worker_id=worker_id,
            config=config or {}
        )
        
        # Executor-specific state
        self.active_executions: Dict[str, TaskExecution] = {}
        self.completed_executions: Dict[str, TaskExecution] = {}
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        
        # Execution capabilities
        self.max_concurrent_tasks = config.get('max_concurrent_tasks', 3)
        self.progress_report_interval = config.get('progress_report_interval', 30)  # seconds
        self.auto_verification_request = config.get('auto_verification_request', True)
        
        # Enhanced tool usage tracking
        self.tool_usage_stats: Dict[str, Dict[str, Any]] = {}
        self.enhanced_tools: Dict[str, Any] = {}
        
        # Override message handlers for executor-specific behavior
        self._setup_executor_message_handlers()
        
        self.logger.info(f"ExecutorWorker {name} initialized")
    
    def execute_assigned_task(self, task_description: str, task_parameters: Optional[Dict[str, Any]] = None,
                            assignment_id: Optional[str] = None, assigned_by: Optional[str] = None) -> str:
        """
        Execute an assigned task with progress tracking.
        
        Args:
            task_description: Description of the task to execute
            task_parameters: Optional task parameters
            assignment_id: Optional assignment ID from planner
            assigned_by: Optional ID of the assigning worker
            
        Returns:
            Execution ID for tracking
            
        Raises:
            WorkerError: If task execution cannot be started
        """
        if len(self.active_executions) >= self.max_concurrent_tasks:
            raise WorkerError(
                f"Maximum concurrent tasks reached: {self.max_concurrent_tasks}",
                worker_id=self.worker_id,
                context={'active_tasks': len(self.active_executions)}
            )
        
        # Create task execution
        execution_id = str(uuid.uuid4())
        task_execution = TaskExecution(
            execution_id=execution_id,
            assignment_id=assignment_id,
            task_description=task_description,
            task_parameters=task_parameters or {},
            assigned_by=assigned_by,
            status=TaskStatus.PENDING
        )
        
        # Store execution
        self.active_executions[execution_id] = task_execution
        
        # Start execution in background
        self._start_task_execution(execution_id)
        
        self.logger.info(f"Started task execution: {execution_id}")
        return execution_id
    
    def report_progress_to_planner(self, planner_id: str, execution_id: str,
                                 progress_percentage: float, current_step: str,
                                 details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Report execution progress to a planner.
        
        Args:
            planner_id: ID of the planner to report to
            execution_id: ID of the task execution
            progress_percentage: Current progress (0-100)
            current_step: Description of current step
            details: Optional additional details
            
        Returns:
            True if progress report was sent successfully
        """
        if execution_id not in self.active_executions:
            self.logger.warning(f"Execution {execution_id} not found")
            return False
        
        # Create progress report
        progress_report = ProgressReport(
            execution_id=execution_id,
            progress_percentage=progress_percentage,
            status=self.active_executions[execution_id].status,
            current_step=current_step,
            details=details
        )
        
        # Send progress message
        message = {
            'message_type': MessageType.STATUS_UPDATE.value,
            'execution_id': execution_id,
            'progress_report': {
                'progress_percentage': progress_report.progress_percentage,
                'status': progress_report.status.value,
                'current_step': progress_report.current_step,
                'details': progress_report.details,
                'timestamp': progress_report.timestamp.isoformat()
            },
            'worker_name': self.name,
            'worker_type': self.worker_type.value
        }
        
        success = self.send_message_to_worker(planner_id, message)
        
        if success:
            # Update execution progress
            self.active_executions[execution_id].progress_percentage = progress_percentage
            self.logger.debug(f"Progress reported to {planner_id}: {progress_percentage}%")
        
        return success
    
    def request_verification_from_verifier(self, verifier_id: str, execution_id: str,
                                         output_to_verify: Any,
                                         verification_criteria: Optional[Dict[str, Any]] = None) -> bool:
        """
        Request verification of execution output from a verifier.
        
        Args:
            verifier_id: ID of the verifier worker
            execution_id: ID of the task execution
            output_to_verify: Output that needs verification
            verification_criteria: Optional verification criteria
            
        Returns:
            True if verification request was sent
        """
        if execution_id not in self.active_executions:
            self.logger.warning(f"Execution {execution_id} not found")
            return False
        
        # Enhanced verification request with execution context
        message = {
            'message_type': MessageType.VERIFICATION_REQUEST.value,
            'execution_id': execution_id,
            'output_to_verify': output_to_verify,
            'verification_criteria': verification_criteria or {},
            'task_description': self.active_executions[execution_id].task_description,
            'task_parameters': self.active_executions[execution_id].task_parameters,
            'requested_by': self.worker_id,
            'requested_at': datetime.now().isoformat(),
            'requires_response': True
        }
        
        success = self.send_message_to_worker(verifier_id, message)
        
        if success:
            self.logger.info(f"Verification requested from {verifier_id} for execution {execution_id}")
        
        return success
    
    def use_enhanced_tool(self, tool_name: str, parameters: Dict[str, Any],
                         execution_id: Optional[str] = None) -> Any:
        """
        Use an enhanced tool with usage tracking.
        
        Args:
            tool_name: Name of the tool to use
            parameters: Tool parameters
            execution_id: Optional execution ID for tracking
            
        Returns:
            Tool execution result
            
        Raises:
            WorkerError: If tool usage fails
        """
        try:
            # Track tool usage
            if tool_name not in self.tool_usage_stats:
                self.tool_usage_stats[tool_name] = {
                    'usage_count': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'last_used': None,
                    'average_duration': 0.0
                }
            
            start_time = datetime.now()
            self.tool_usage_stats[tool_name]['usage_count'] += 1
            
            # Use the tool (delegate to base task executor or enhanced tool system)
            if hasattr(self.task_executor, 'use_tool'):
                result = self.task_executor.use_tool(tool_name, parameters)
            else:
                # Fallback to basic tool usage
                result = self._use_basic_tool(tool_name, parameters)
            
            # Track success
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            stats = self.tool_usage_stats[tool_name]
            stats['success_count'] += 1
            stats['last_used'] = end_time
            stats['average_duration'] = (stats['average_duration'] * (stats['success_count'] - 1) + duration) / stats['success_count']
            
            # Update execution progress if applicable
            if execution_id and execution_id in self.active_executions:
                execution = self.active_executions[execution_id]
                execution.progress_percentage = min(execution.progress_percentage + 10, 100)
            
            self.logger.debug(f"Successfully used tool {tool_name}")
            return result
            
        except Exception as e:
            # Track failure
            self.tool_usage_stats[tool_name]['failure_count'] += 1
            
            self.logger.error(f"Tool usage failed for {tool_name}: {e}")
            raise WorkerError(
                f"Enhanced tool usage failed: {e}",
                worker_id=self.worker_id,
                context={'tool_name': tool_name, 'parameters': parameters, 'error': str(e)}
            )
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a task execution.
        
        Args:
            execution_id: ID of the task execution
            
        Returns:
            Dictionary containing execution status or None if not found
        """
        execution = self.active_executions.get(execution_id) or self.completed_executions.get(execution_id)
        
        if not execution:
            return None
        
        return {
            'execution_id': execution.execution_id,
            'assignment_id': execution.assignment_id,
            'task_description': execution.task_description,
            'status': execution.status.value,
            'progress_percentage': execution.progress_percentage,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'assigned_by': execution.assigned_by,
            'has_result': execution.result is not None,
            'has_error': execution.error_details is not None
        }
    
    def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel an active task execution.
        
        Args:
            execution_id: ID of the task execution to cancel
            
        Returns:
            True if cancellation was successful
        """
        if execution_id not in self.active_executions:
            self.logger.warning(f"Execution {execution_id} not found or not active")
            return False
        
        execution = self.active_executions[execution_id]
        execution.status = TaskStatus.CANCELLED
        execution.completed_at = datetime.now()
        
        # Move to completed executions
        self.completed_executions[execution_id] = execution
        del self.active_executions[execution_id]
        
        self.logger.info(f"Cancelled task execution: {execution_id}")
        return True
    
    def get_executor_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for this executor.
        
        Returns:
            Dictionary containing executor statistics
        """
        base_stats = self.get_collaboration_statistics()
        
        executor_stats = {
            'active_executions': len(self.active_executions),
            'completed_executions': len(self.completed_executions),
            'total_executions': len(self.active_executions) + len(self.completed_executions),
            'tool_usage_stats': self.tool_usage_stats,
            'execution_breakdown': {
                'pending': len([e for e in self.active_executions.values() if e.status == TaskStatus.PENDING]),
                'in_progress': len([e for e in self.active_executions.values() if e.status == TaskStatus.IN_PROGRESS]),
                'completed': len([e for e in self.completed_executions.values() if e.status == TaskStatus.COMPLETED]),
                'failed': len([e for e in self.completed_executions.values() if e.status == TaskStatus.FAILED]),
                'cancelled': len([e for e in self.completed_executions.values() if e.status == TaskStatus.CANCELLED])
            }
        }
        
        return {**base_stats, **executor_stats}
    
    def _start_task_execution(self, execution_id: str) -> None:
        """
        Start executing a task in the background.
        
        Args:
            execution_id: ID of the task execution
        """
        execution = self.active_executions[execution_id]
        
        try:
            # Update status to in progress
            execution.status = TaskStatus.IN_PROGRESS
            execution.started_at = datetime.now()
            
            # Report start to planner if assigned
            if execution.assigned_by:
                self.report_progress_to_planner(
                    execution.assigned_by, execution_id, 0.0, "Starting task execution"
                )
            
            # Execute the task (simplified implementation)
            result = self._execute_task_logic(execution)
            
            # Update execution with result
            execution.result = result
            execution.status = TaskStatus.COMPLETED
            execution.completed_at = datetime.now()
            execution.progress_percentage = 100.0
            
            # Report completion to planner
            if execution.assigned_by:
                self._send_completion_report(execution)
            
            # Request verification if enabled
            if self.auto_verification_request and execution.assigned_by:
                self._request_auto_verification(execution)
            
            # Move to completed executions
            self.completed_executions[execution_id] = execution
            del self.active_executions[execution_id]
            
            self.logger.info(f"Task execution completed: {execution_id}")
            
        except Exception as e:
            # Handle execution failure
            execution.status = TaskStatus.FAILED
            execution.completed_at = datetime.now()
            execution.error_details = {
                'error_message': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }
            
            # Report failure to planner
            if execution.assigned_by:
                self._send_failure_report(execution)
            
            # Move to completed executions
            self.completed_executions[execution_id] = execution
            del self.active_executions[execution_id]
            
            self.logger.error(f"Task execution failed: {execution_id} - {e}")
    
    def _execute_task_logic(self, execution: TaskExecution) -> Any:
        """
        Execute the actual task logic.
        
        Args:
            execution: TaskExecution instance
            
        Returns:
            Task execution result
        """
        # Simplified task execution - can be enhanced with actual task processing
        task_description = execution.task_description
        task_parameters = execution.task_parameters
        
        # Report progress
        if execution.assigned_by:
            self.report_progress_to_planner(
                execution.assigned_by, execution.execution_id, 25.0, "Processing task"
            )
        
        # Use enhanced tools if specified
        if 'tools' in task_parameters:
            tools_to_use = task_parameters['tools']
            for tool_name, tool_params in tools_to_use.items():
                self.use_enhanced_tool(tool_name, tool_params, execution.execution_id)
        
        # Report more progress
        if execution.assigned_by:
            self.report_progress_to_planner(
                execution.assigned_by, execution.execution_id, 75.0, "Finalizing task"
            )
        
        # Return a simple result (can be enhanced with actual task processing)
        return {
            'task_completed': True,
            'description': task_description,
            'parameters_used': task_parameters,
            'execution_time': datetime.now().isoformat(),
            'executor_id': self.worker_id
        }
    
    def _use_basic_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Basic tool usage fallback.
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            
        Returns:
            Tool result
        """
        # Placeholder for basic tool usage
        return {
            'tool_used': tool_name,
            'parameters': parameters,
            'result': f"Tool {tool_name} executed successfully",
            'timestamp': datetime.now().isoformat()
        }
    
    def _send_completion_report(self, execution: TaskExecution) -> None:
        """Send completion report to planner."""
        message = {
            'message_type': MessageType.RESULT_REPORT.value,
            'execution_id': execution.execution_id,
            'assignment_id': execution.assignment_id,
            'status': 'completed',
            'result': execution.result,
            'completed_at': execution.completed_at.isoformat(),
            'executor_id': self.worker_id
        }
        
        self.send_message_to_worker(execution.assigned_by, message)
    
    def _send_failure_report(self, execution: TaskExecution) -> None:
        """Send failure report to planner."""
        message = {
            'message_type': MessageType.ERROR_NOTIFICATION.value,
            'execution_id': execution.execution_id,
            'assignment_id': execution.assignment_id,
            'status': 'failed',
            'error_details': execution.error_details,
            'failed_at': execution.completed_at.isoformat(),
            'executor_id': self.worker_id
        }
        
        self.send_message_to_worker(execution.assigned_by, message)
    
    def _request_auto_verification(self, execution: TaskExecution) -> None:
        """Request automatic verification if verifier is available."""
        if not self._is_connected:
            return
        
        try:
            server = self.server_connection.server_instance
            worker_registry = server.get_worker_registry()
            
            # Find available verifier
            verifiers = worker_registry.find_workers_by_type(WorkerType.VERIFIER)
            if verifiers:
                verifier_id = verifiers[0].worker_id
                self.request_verification_from_verifier(
                    verifier_id, execution.execution_id, execution.result
                )
        except Exception as e:
            self.logger.warning(f"Auto verification request failed: {e}")
    
    def _setup_executor_message_handlers(self) -> None:
        """Setup executor-specific message handlers."""
        # Override task delegation handler for executor-specific behavior
        self.message_handlers[MessageType.TASK_DELEGATION] = self._handle_executor_task_delegation
    
    def _handle_executor_task_delegation(self, message) -> None:
        """Handle task delegation messages for executors."""
        assignment_id = message.content.get('assignment_id')
        task_description = message.content.get('task_description', '')
        task_parameters = message.content.get('task_parameters', {})
        assigned_by = message.from_worker_id
        
        try:
            # Start task execution
            execution_id = self.execute_assigned_task(
                task_description=task_description,
                task_parameters=task_parameters,
                assignment_id=assignment_id,
                assigned_by=assigned_by
            )
            
            self.logger.info(f"Accepted task delegation from {assigned_by}: {task_description}")
            
        except WorkerError as e:
            # Send error response
            error_message = {
                'message_type': MessageType.ERROR_NOTIFICATION.value,
                'assignment_id': assignment_id,
                'error_details': {
                    'error_message': str(e),
                    'error_type': 'task_delegation_failed',
                    'timestamp': datetime.now().isoformat()
                },
                'executor_id': self.worker_id
            }
            
            self.send_message_to_worker(assigned_by, error_message)
            self.logger.error(f"Task delegation failed: {e}")
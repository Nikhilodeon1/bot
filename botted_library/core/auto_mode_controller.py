"""
Auto Mode Controller for Collaborative Worker System

Provides automated operations with flowchart execution, initial planner creation,
and objective analysis for autonomous worker management.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .enhanced_worker_registry import WorkerType, WorkerFlowchart
from .exceptions import WorkerError


class FlowchartStatus(Enum):
    """Status of flowchart execution"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionStep:
    """Represents a step in flowchart execution"""
    step_id: str
    step_type: str  # create_worker, assign_task, wait_for_completion, verify_output
    parameters: Dict[str, Any]
    dependencies: List[str]  # List of step IDs that must complete first
    status: str = "pending"  # pending, in_progress, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ObjectiveAnalysis:
    """Analysis of user objectives for auto mode planning"""
    objectives: str
    complexity_score: int  # 1-10 scale
    estimated_duration: timedelta
    required_worker_types: Dict[WorkerType, int]
    key_capabilities: List[str]
    success_criteria: Dict[str, Any]
    risk_factors: List[str]
    recommended_approach: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'objectives': self.objectives,
            'complexity_score': self.complexity_score,
            'estimated_duration': self.estimated_duration.total_seconds(),
            'required_worker_types': {wt.value: count for wt, count in self.required_worker_types.items()},
            'key_capabilities': self.key_capabilities,
            'success_criteria': self.success_criteria,
            'risk_factors': self.risk_factors,
            'recommended_approach': self.recommended_approach
        }


class AutoModeController:
    """
    Controller for automated mode operations where an initial planner
    automatically creates and manages workers based on objectives.
    
    In auto mode, the system:
    - Analyzes user objectives automatically
    - Creates an initial planner worker
    - Generates flowcharts for optimal worker interactions
    - Automatically scales workers based on workload
    - Monitors and adjusts execution dynamically
    """
    
    def __init__(self, server_instance, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the auto mode controller.
        
        Args:
            server_instance: Reference to the collaborative server
            config: Optional configuration parameters
        """
        self.server = server_instance
        self.config = config or {}
        self.controller_id = str(uuid.uuid4())
        
        # Setup logging
        self.logger = logging.getLogger(f"AutoModeController.{self.controller_id[:8]}")
        
        # Auto mode state
        self.initial_planner: Optional[Any] = None
        self.active_flowcharts: Dict[str, WorkerFlowchart] = {}
        self.execution_steps: Dict[str, ExecutionStep] = {}
        self.auto_workers: Dict[str, Dict[str, Any]] = {}
        self.objective_analyses: Dict[str, ObjectiveAnalysis] = {}
        
        # Execution monitoring
        self.execution_status = {
            'is_active': False,
            'current_objectives': None,
            'active_flowchart_id': None,
            'workers_created': 0,
            'tasks_completed': 0,
            'execution_start_time': None
        }
        
        # Auto scaling configuration
        self.auto_scaling_config = {
            'max_workers_per_type': self.config.get('max_workers_per_type', 10),
            'scale_up_threshold': self.config.get('scale_up_threshold', 0.8),
            'scale_down_threshold': self.config.get('scale_down_threshold', 0.3),
            'monitoring_interval': self.config.get('monitoring_interval', 30)
        }
        
        # Statistics
        self.stats = {
            'objectives_analyzed': 0,
            'flowcharts_created': 0,
            'workers_auto_created': 0,
            'auto_scaling_events': 0,
            'execution_cycles': 0
        }
        
        self.logger.info(f"AutoModeController initialized with ID: {self.controller_id[:8]}")
    
    def initialize_auto_mode(self, objectives: str, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Initialize auto mode with user objectives.
        
        Args:
            objectives: User's objectives and goals
            config: Optional configuration for auto mode execution
            
        Returns:
            Analysis ID for the initialized auto mode session
            
        Raises:
            WorkerError: If initialization fails
        """
        try:
            self.logger.info(f"Initializing auto mode with objectives: {objectives[:100]}...")
            
            # Analyze objectives
            analysis = self._analyze_objectives(objectives)
            analysis_id = str(uuid.uuid4())
            self.objective_analyses[analysis_id] = analysis
            
            # Create initial planner
            initial_planner = self.create_initial_planner(objectives, analysis)
            
            # Generate flowchart based on analysis
            flowchart = self._create_execution_flowchart(analysis, initial_planner.worker_id)
            
            # Update execution status
            self.execution_status.update({
                'is_active': True,
                'current_objectives': objectives,
                'active_flowchart_id': flowchart.flowchart_id,
                'execution_start_time': datetime.now()
            })
            
            self.stats['objectives_analyzed'] += 1
            
            self.logger.info(f"Auto mode initialized successfully with analysis ID: {analysis_id}")
            
            return analysis_id
            
        except Exception as e:
            self.logger.error(f"Auto mode initialization failed: {e}")
            raise WorkerError(
                f"Auto mode initialization failed: {e}",
                worker_id=self.controller_id,
                context={'operation': 'initialize_auto_mode', 'error': str(e)}
            )
    
    def create_initial_planner(self, objectives: str, analysis: Optional[ObjectiveAnalysis] = None) -> Any:
        """
        Create the initial planner worker for auto mode.
        
        Args:
            objectives: User objectives
            analysis: Optional pre-computed objective analysis
            
        Returns:
            Initial planner worker instance
            
        Raises:
            WorkerError: If planner creation fails
        """
        try:
            # Import here to avoid circular imports
            from .planner_worker import PlannerWorker
            from .enhanced_worker import ServerConnection
            
            # Generate worker ID
            worker_id = str(uuid.uuid4())
            
            # Create server connection
            server_connection = ServerConnection(
                server_instance=self.server,
                worker_id=worker_id,
                connection_id=str(uuid.uuid4()),
                connected_at=datetime.now()
            )
            
            # Configure initial planner
            planner_config = {
                'auto_mode': True,
                'is_initial_planner': True,
                'objectives': objectives,
                'analysis': analysis.to_dict() if analysis else None,
                'controller_id': self.controller_id,
                'auto_scaling_enabled': True,
                'max_workers_per_type': self.auto_scaling_config['max_workers_per_type']
            }
            
            # Create initial planner
            initial_planner = PlannerWorker(
                name="Initial Planner",
                role="Auto Mode Coordinator",
                memory_system=None,  # Will be initialized by worker
                knowledge_validator=None,  # Will be initialized by worker
                browser_controller=None,  # Will be initialized by worker
                task_executor=None,  # Will be initialized by worker
                server_connection=server_connection,
                worker_id=worker_id,
                config=planner_config
            )
            
            # Connect to server
            initial_planner.connect_to_server()
            
            # Store reference
            self.initial_planner = initial_planner
            
            # Track in auto workers
            self.auto_workers[worker_id] = {
                'worker_instance': initial_planner,
                'worker_type': WorkerType.PLANNER,
                'name': 'Initial Planner',
                'role': 'Auto Mode Coordinator',
                'created_at': datetime.now(),
                'created_by': 'auto_controller',
                'is_initial_planner': True,
                'status': 'active'
            }
            
            self.execution_status['workers_created'] += 1
            self.stats['workers_auto_created'] += 1
            
            self.logger.info(f"Initial planner created successfully: {worker_id}")
            
            return initial_planner
            
        except Exception as e:
            self.logger.error(f"Initial planner creation failed: {e}")
            raise WorkerError(
                f"Initial planner creation failed: {e}",
                worker_id=worker_id if 'worker_id' in locals() else None,
                context={'operation': 'create_initial_planner', 'error': str(e)}
            )
    
    def execute_flowchart(self, flowchart: WorkerFlowchart) -> bool:
        """
        Execute a worker flowchart automatically.
        
        Args:
            flowchart: WorkerFlowchart to execute
            
        Returns:
            True if execution started successfully
            
        Raises:
            WorkerError: If flowchart execution fails to start
        """
        try:
            self.logger.info(f"Starting flowchart execution: {flowchart.flowchart_id}")
            
            # Validate flowchart
            if not self._validate_flowchart(flowchart):
                raise WorkerError(
                    "Flowchart validation failed",
                    worker_id=self.controller_id,
                    context={'operation': 'execute_flowchart', 'flowchart_id': flowchart.flowchart_id}
                )
            
            # Update flowchart status
            flowchart.status = FlowchartStatus.ACTIVE.value
            self.active_flowcharts[flowchart.flowchart_id] = flowchart
            
            # Create execution steps from flowchart
            execution_steps = self._create_execution_steps(flowchart)
            
            # Start execution
            self._start_flowchart_execution(flowchart.flowchart_id, execution_steps)
            
            self.stats['execution_cycles'] += 1
            
            self.logger.info(f"Flowchart execution started: {flowchart.flowchart_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Flowchart execution failed: {e}")
            raise WorkerError(
                f"Flowchart execution failed: {e}",
                worker_id=self.controller_id,
                context={'operation': 'execute_flowchart', 'error': str(e)}
            )
    
    def monitor_auto_execution(self) -> Dict[str, Any]:
        """
        Monitor the current auto mode execution status.
        
        Returns:
            Dictionary containing execution status and metrics
        """
        try:
            # Calculate execution metrics
            execution_time = None
            if self.execution_status['execution_start_time']:
                execution_time = (datetime.now() - self.execution_status['execution_start_time']).total_seconds()
            
            # Get worker statistics
            active_workers_by_type = {}
            for worker_info in self.auto_workers.values():
                if worker_info['status'] == 'active':
                    worker_type = worker_info['worker_type'].value
                    active_workers_by_type[worker_type] = active_workers_by_type.get(worker_type, 0) + 1
            
            # Get flowchart progress
            flowchart_progress = {}
            if self.execution_status['active_flowchart_id']:
                flowchart_id = self.execution_status['active_flowchart_id']
                if flowchart_id in self.active_flowcharts:
                    flowchart_progress = self._calculate_flowchart_progress(flowchart_id)
            
            return {
                'controller_id': self.controller_id,
                'execution_status': self.execution_status,
                'execution_time_seconds': execution_time,
                'active_workers_by_type': active_workers_by_type,
                'total_auto_workers': len([w for w in self.auto_workers.values() if w['status'] == 'active']),
                'flowchart_progress': flowchart_progress,
                'statistics': self.stats,
                'auto_scaling_config': self.auto_scaling_config
            }
            
        except Exception as e:
            self.logger.error(f"Error monitoring auto execution: {e}")
            return {'error': str(e)}
    
    def pause_auto_execution(self) -> bool:
        """
        Pause the current auto mode execution.
        
        Returns:
            True if paused successfully
        """
        try:
            if not self.execution_status['is_active']:
                self.logger.warning("No active auto execution to pause")
                return False
            
            # Pause active flowcharts
            for flowchart in self.active_flowcharts.values():
                if flowchart.status == FlowchartStatus.ACTIVE.value:
                    flowchart.status = FlowchartStatus.PAUSED.value
            
            self.execution_status['is_active'] = False
            
            self.logger.info("Auto execution paused")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pause auto execution: {e}")
            return False
    
    def resume_auto_execution(self) -> bool:
        """
        Resume paused auto mode execution.
        
        Returns:
            True if resumed successfully
        """
        try:
            # Resume paused flowcharts
            resumed_count = 0
            for flowchart in self.active_flowcharts.values():
                if flowchart.status == FlowchartStatus.PAUSED.value:
                    flowchart.status = FlowchartStatus.ACTIVE.value
                    resumed_count += 1
            
            if resumed_count > 0:
                self.execution_status['is_active'] = True
                self.logger.info(f"Auto execution resumed ({resumed_count} flowcharts)")
                return True
            else:
                self.logger.warning("No paused flowcharts to resume")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to resume auto execution: {e}")
            return False
    
    def stop_auto_execution(self) -> bool:
        """
        Stop the current auto mode execution.
        
        Returns:
            True if stopped successfully
        """
        try:
            # Stop active flowcharts
            for flowchart in self.active_flowcharts.values():
                if flowchart.status in [FlowchartStatus.ACTIVE.value, FlowchartStatus.PAUSED.value]:
                    flowchart.status = FlowchartStatus.CANCELLED.value
            
            # Reset execution status
            self.execution_status.update({
                'is_active': False,
                'current_objectives': None,
                'active_flowchart_id': None,
                'execution_start_time': None
            })
            
            self.logger.info("Auto execution stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop auto execution: {e}")
            return False
    
    def _analyze_objectives(self, objectives: str) -> ObjectiveAnalysis:
        """
        Analyze user objectives to determine execution strategy.
        
        Args:
            objectives: User objectives string
            
        Returns:
            ObjectiveAnalysis with planning recommendations
        """
        # Simple objective analysis (in a real implementation, this would use NLP/ML)
        complexity_indicators = ['complex', 'multiple', 'integrate', 'coordinate', 'analyze']
        complexity_score = sum(1 for indicator in complexity_indicators if indicator in objectives.lower())
        complexity_score = min(max(complexity_score, 1), 10)
        
        # Estimate required workers based on keywords
        required_workers = {WorkerType.PLANNER: 1}  # Always need at least one planner
        
        if any(word in objectives.lower() for word in ['execute', 'perform', 'run', 'do']):
            required_workers[WorkerType.EXECUTOR] = max(1, complexity_score // 3)
        
        if any(word in objectives.lower() for word in ['verify', 'check', 'validate', 'quality']):
            required_workers[WorkerType.VERIFIER] = max(1, complexity_score // 4)
        
        # Estimate duration based on complexity
        base_duration = timedelta(minutes=30)
        estimated_duration = base_duration * complexity_score
        
        # Identify key capabilities needed
        capability_keywords = {
            'web_browsing': ['web', 'browser', 'website', 'online'],
            'data_analysis': ['analyze', 'data', 'statistics', 'report'],
            'file_processing': ['file', 'document', 'process', 'convert'],
            'communication': ['email', 'message', 'notify', 'communicate']
        }
        
        key_capabilities = []
        for capability, keywords in capability_keywords.items():
            if any(keyword in objectives.lower() for keyword in keywords):
                key_capabilities.append(capability)
        
        # Define success criteria
        success_criteria = {
            'completion_rate': 0.95,
            'quality_threshold': 0.8,
            'time_limit': estimated_duration.total_seconds(),
            'error_tolerance': 0.05
        }
        
        # Identify risk factors
        risk_factors = []
        if complexity_score > 7:
            risk_factors.append('High complexity may require additional coordination')
        if len(required_workers) > 2:
            risk_factors.append('Multiple worker types increase coordination overhead')
        if estimated_duration > timedelta(hours=2):
            risk_factors.append('Long execution time increases failure risk')
        
        # Recommend approach
        if complexity_score <= 3:
            recommended_approach = "Simple sequential execution with minimal coordination"
        elif complexity_score <= 6:
            recommended_approach = "Moderate parallel execution with regular checkpoints"
        else:
            recommended_approach = "Complex orchestrated execution with continuous monitoring"
        
        return ObjectiveAnalysis(
            objectives=objectives,
            complexity_score=complexity_score,
            estimated_duration=estimated_duration,
            required_worker_types=required_workers,
            key_capabilities=key_capabilities,
            success_criteria=success_criteria,
            risk_factors=risk_factors,
            recommended_approach=recommended_approach
        )
    
    def _create_execution_flowchart(self, analysis: ObjectiveAnalysis, initial_planner_id: str) -> WorkerFlowchart:
        """
        Create a flowchart based on objective analysis.
        
        Args:
            analysis: ObjectiveAnalysis containing planning information
            initial_planner_id: ID of the initial planner worker
            
        Returns:
            WorkerFlowchart for execution
        """
        flowchart_id = str(uuid.uuid4())
        
        # Create interaction patterns based on analysis
        interaction_patterns = []
        
        # Basic planner -> executor pattern
        if WorkerType.EXECUTOR in analysis.required_worker_types:
            interaction_patterns.append({
                'pattern_id': str(uuid.uuid4()),
                'from_worker_type': WorkerType.PLANNER.value,
                'to_worker_type': WorkerType.EXECUTOR.value,
                'interaction_type': 'DELEGATE',
                'conditions': {'task_complexity': 'any'},
                'parameters': {'max_concurrent_tasks': 3}
            })
        
        # Executor -> verifier pattern
        if WorkerType.VERIFIER in analysis.required_worker_types:
            interaction_patterns.append({
                'pattern_id': str(uuid.uuid4()),
                'from_worker_type': WorkerType.EXECUTOR.value,
                'to_worker_type': WorkerType.VERIFIER.value,
                'interaction_type': 'VERIFY',
                'conditions': {'requires_verification': True},
                'parameters': {'quality_threshold': analysis.success_criteria['quality_threshold']}
            })
        
        # Create execution order
        execution_order = [
            f"create_workers_{worker_type.value}_{count}"
            for worker_type, count in analysis.required_worker_types.items()
            if worker_type != WorkerType.PLANNER  # Planner already exists
        ]
        execution_order.append("assign_initial_tasks")
        execution_order.append("monitor_execution")
        execution_order.append("verify_results")
        
        flowchart = WorkerFlowchart(
            flowchart_id=flowchart_id,
            objectives=analysis.objectives,
            planner_count=analysis.required_worker_types.get(WorkerType.PLANNER, 1),
            executor_count=analysis.required_worker_types.get(WorkerType.EXECUTOR, 0),
            verifier_count=analysis.required_worker_types.get(WorkerType.VERIFIER, 0),
            interaction_patterns=interaction_patterns,
            execution_order=execution_order,
            success_criteria=analysis.success_criteria,
            created_by=initial_planner_id,
            created_at=datetime.now(),
            status=FlowchartStatus.DRAFT.value
        )
        
        self.stats['flowcharts_created'] += 1
        
        return flowchart
    
    def _validate_flowchart(self, flowchart: WorkerFlowchart) -> bool:
        """
        Validate a flowchart before execution.
        
        Args:
            flowchart: WorkerFlowchart to validate
            
        Returns:
            True if flowchart is valid
        """
        try:
            # Check required fields
            if not flowchart.flowchart_id or not flowchart.objectives:
                return False
            
            # Check worker counts are reasonable
            total_workers = flowchart.planner_count + flowchart.executor_count + flowchart.verifier_count
            if total_workers > self.auto_scaling_config['max_workers_per_type'] * 3:
                self.logger.warning(f"Flowchart requires too many workers: {total_workers}")
                return False
            
            # Check execution order is not empty
            if not flowchart.execution_order:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Flowchart validation error: {e}")
            return False
    
    def _create_execution_steps(self, flowchart: WorkerFlowchart) -> List[ExecutionStep]:
        """
        Create execution steps from a flowchart.
        
        Args:
            flowchart: WorkerFlowchart to convert to steps
            
        Returns:
            List of ExecutionStep objects
        """
        steps = []
        
        # Create worker creation steps
        if flowchart.executor_count > 0:
            steps.append(ExecutionStep(
                step_id=str(uuid.uuid4()),
                step_type="create_workers",
                parameters={
                    'worker_type': WorkerType.EXECUTOR.value,
                    'count': flowchart.executor_count,
                    'capabilities': ['task_execution', 'tool_usage']
                },
                dependencies=[]
            ))
        
        if flowchart.verifier_count > 0:
            steps.append(ExecutionStep(
                step_id=str(uuid.uuid4()),
                step_type="create_workers",
                parameters={
                    'worker_type': WorkerType.VERIFIER.value,
                    'count': flowchart.verifier_count,
                    'capabilities': ['quality_validation', 'output_verification']
                },
                dependencies=[]
            ))
        
        # Add task assignment step
        worker_creation_steps = [s.step_id for s in steps if s.step_type == "create_workers"]
        steps.append(ExecutionStep(
            step_id=str(uuid.uuid4()),
            step_type="assign_initial_tasks",
            parameters={
                'objectives': flowchart.objectives,
                'success_criteria': flowchart.success_criteria
            },
            dependencies=worker_creation_steps
        ))
        
        return steps
    
    def _start_flowchart_execution(self, flowchart_id: str, execution_steps: List[ExecutionStep]) -> None:
        """
        Start executing a flowchart with the given steps.
        
        Args:
            flowchart_id: ID of the flowchart to execute
            execution_steps: List of execution steps
        """
        # Store execution steps
        for step in execution_steps:
            self.execution_steps[step.step_id] = step
        
        # Start executing steps (simplified implementation)
        # In a real implementation, this would be more sophisticated with proper scheduling
        for step in execution_steps:
            if not step.dependencies:  # Steps with no dependencies can start immediately
                self._execute_step(step)
    
    def _execute_step(self, step: ExecutionStep) -> None:
        """
        Execute a single flowchart step.
        
        Args:
            step: ExecutionStep to execute
        """
        try:
            step.status = "in_progress"
            step.started_at = datetime.now()
            
            if step.step_type == "create_workers":
                self._execute_create_workers_step(step)
            elif step.step_type == "assign_initial_tasks":
                self._execute_assign_tasks_step(step)
            else:
                self.logger.warning(f"Unknown step type: {step.step_type}")
                step.status = "failed"
                step.error = f"Unknown step type: {step.step_type}"
                return
            
            step.status = "completed"
            step.completed_at = datetime.now()
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.now()
            self.logger.error(f"Step execution failed: {e}")
    
    def _execute_create_workers_step(self, step: ExecutionStep) -> None:
        """Execute a create workers step."""
        worker_type_str = step.parameters['worker_type']
        count = step.parameters['count']
        capabilities = step.parameters.get('capabilities', [])
        
        worker_type = WorkerType(worker_type_str)
        created_workers = []
        
        for i in range(count):
            worker_id = self._create_auto_worker(
                worker_type=worker_type,
                name=f"Auto {worker_type_str.title()} {i+1}",
                role=f"Automated {worker_type_str.title()}",
                capabilities=capabilities
            )
            created_workers.append(worker_id)
        
        step.result = {'created_workers': created_workers}
    
    def _execute_assign_tasks_step(self, step: ExecutionStep) -> None:
        """Execute an assign tasks step."""
        objectives = step.parameters['objectives']
        
        # Use initial planner to assign tasks
        if self.initial_planner:
            # This would involve more sophisticated task breakdown and assignment
            # For now, just log the assignment
            self.logger.info(f"Initial planner assigning tasks for objectives: {objectives[:100]}...")
            step.result = {'tasks_assigned': True}
    
    def _create_auto_worker(self, worker_type: WorkerType, name: str, role: str,
                           capabilities: Optional[List[str]] = None) -> str:
        """
        Create a worker automatically as part of flowchart execution.
        
        Args:
            worker_type: Type of worker to create
            name: Worker name
            role: Worker role
            capabilities: Optional capabilities list
            
        Returns:
            Worker ID of created worker
        """
        # Import here to avoid circular imports
        from .planner_worker import PlannerWorker
        from .executor_worker import ExecutorWorker
        from .verifier_worker import VerifierWorker
        from .enhanced_worker import ServerConnection
        
        worker_id = str(uuid.uuid4())
        
        # Create server connection
        server_connection = ServerConnection(
            server_instance=self.server,
            worker_id=worker_id,
            connection_id=str(uuid.uuid4()),
            connected_at=datetime.now()
        )
        
        # Configure worker
        worker_config = {
            'auto_mode': True,
            'created_by_controller': self.controller_id,
            'capabilities': capabilities or []
        }
        
        # Create worker based on type
        if worker_type == WorkerType.PLANNER:
            worker = PlannerWorker(
                name=name, role=role,
                memory_system=None, knowledge_validator=None,
                browser_controller=None, task_executor=None,
                server_connection=server_connection,
                worker_id=worker_id, config=worker_config
            )
        elif worker_type == WorkerType.EXECUTOR:
            worker = ExecutorWorker(
                name=name, role=role,
                memory_system=None, knowledge_validator=None,
                browser_controller=None, task_executor=None,
                server_connection=server_connection,
                worker_id=worker_id, config=worker_config
            )
        elif worker_type == WorkerType.VERIFIER:
            worker = VerifierWorker(
                name=name, role=role,
                memory_system=None, knowledge_validator=None,
                browser_controller=None, task_executor=None,
                server_connection=server_connection,
                worker_id=worker_id, config=worker_config
            )
        else:
            raise WorkerError(f"Unsupported worker type: {worker_type}")
        
        # Connect to server
        worker.connect_to_server()
        
        # Track the auto-created worker
        self.auto_workers[worker_id] = {
            'worker_instance': worker,
            'worker_type': worker_type,
            'name': name,
            'role': role,
            'capabilities': capabilities or [],
            'created_at': datetime.now(),
            'created_by': 'auto_controller',
            'status': 'active'
        }
        
        self.execution_status['workers_created'] += 1
        self.stats['workers_auto_created'] += 1
        
        return worker_id
    
    def _calculate_flowchart_progress(self, flowchart_id: str) -> Dict[str, Any]:
        """
        Calculate progress for a flowchart execution.
        
        Args:
            flowchart_id: ID of the flowchart
            
        Returns:
            Dictionary containing progress information
        """
        flowchart_steps = [step for step in self.execution_steps.values() 
                          if step.step_id in self.active_flowcharts.get(flowchart_id, WorkerFlowchart(
                              flowchart_id="", objectives="", planner_count=0, executor_count=0,
                              verifier_count=0, interaction_patterns=[], execution_order=[],
                              success_criteria={}, created_by="", created_at=datetime.now()
                          )).execution_order]
        
        if not flowchart_steps:
            return {'progress_percentage': 0, 'completed_steps': 0, 'total_steps': 0}
        
        completed_steps = len([step for step in flowchart_steps if step.status == "completed"])
        total_steps = len(flowchart_steps)
        progress_percentage = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
        
        return {
            'progress_percentage': progress_percentage,
            'completed_steps': completed_steps,
            'total_steps': total_steps,
            'failed_steps': len([step for step in flowchart_steps if step.status == "failed"]),
            'in_progress_steps': len([step for step in flowchart_steps if step.status == "in_progress"])
        }
    
    def get_auto_mode_status(self) -> Dict[str, Any]:
        """
        Get comprehensive auto mode status.
        
        Returns:
            Dictionary containing auto mode status and statistics
        """
        return {
            'controller_id': self.controller_id,
            'mode': 'auto',
            'execution_status': self.execution_status,
            'initial_planner_id': self.initial_planner.worker_id if self.initial_planner else None,
            'active_flowcharts': len(self.active_flowcharts),
            'auto_workers': len([w for w in self.auto_workers.values() if w['status'] == 'active']),
            'execution_steps': len(self.execution_steps),
            'statistics': self.stats,
            'auto_scaling_config': self.auto_scaling_config
        }
    
    def shutdown(self) -> None:
        """Shutdown the auto mode controller and cleanup resources."""
        try:
            # Stop any active execution
            self.stop_auto_execution()
            
            # Disconnect all auto workers
            for worker_id, worker_info in self.auto_workers.items():
                try:
                    worker_instance = worker_info['worker_instance']
                    worker_instance.disconnect_from_server()
                    worker_info['status'] = 'disconnected'
                except Exception as e:
                    self.logger.error(f"Error disconnecting auto worker {worker_id}: {e}")
            
            # Clear tracking data
            self.auto_workers.clear()
            self.active_flowcharts.clear()
            self.execution_steps.clear()
            self.objective_analyses.clear()
            self.initial_planner = None
            
            self.logger.info("AutoModeController shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during auto mode controller shutdown: {e}")
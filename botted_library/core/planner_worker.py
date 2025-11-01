"""
Planner Worker Implementation

Specialized worker type that creates strategies, manages other workers,
and coordinates complex task execution workflows.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .enhanced_worker import EnhancedWorker
from .enhanced_worker_registry import WorkerType, WorkerFlowchart
from .message_router import MessageType
from .exceptions import WorkerError


@dataclass
class ExecutionStrategy:
    """Represents an execution strategy created by a planner"""
    strategy_id: str
    objectives: str
    approach: str
    required_workers: Dict[WorkerType, int]
    task_breakdown: List[Dict[str, Any]]
    success_criteria: Dict[str, Any]
    estimated_duration: Optional[int] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class WorkerCreationSpec:
    """Specification for creating a new worker"""
    worker_type: WorkerType
    name: str
    role: str
    capabilities: List[str]
    config: Dict[str, Any]
    priority: int = 5  # 1-10 priority level


class PlannerWorker(EnhancedWorker):
    """
    Planner worker specialization for strategy creation and worker management.
    
    Capabilities:
    - Create execution strategies for complex objectives
    - Create and manage other workers
    - Assign tasks and coordinate execution
    - Design workflow flowcharts
    - Monitor execution progress
    """
    
    def __init__(self, name: str, role: str, memory_system, knowledge_validator,
                 browser_controller, task_executor, server_connection=None,
                 worker_id=None, config=None):
        """
        Initialize planner worker.
        
        Args:
            name: Human-readable name for the planner
            role: Planner's role/title
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
            worker_type=WorkerType.PLANNER,
            memory_system=memory_system,
            knowledge_validator=knowledge_validator,
            browser_controller=browser_controller,
            task_executor=task_executor,
            server_connection=server_connection,
            worker_id=worker_id,
            config=config or {}
        )
        
        # Planner-specific state
        self.created_strategies: Dict[str, ExecutionStrategy] = {}
        self.managed_workers: Dict[str, Dict[str, Any]] = {}
        self.active_flowcharts: Dict[str, WorkerFlowchart] = {}
        self.task_assignments: Dict[str, Dict[str, Any]] = {}
        
        # Planning capabilities
        self.max_concurrent_strategies = config.get('max_concurrent_strategies', 3)
        self.worker_creation_limit = config.get('worker_creation_limit', 10)
        
        # Override message handlers for planner-specific behavior
        self._setup_planner_message_handlers()
        
        self.logger.info(f"PlannerWorker {name} initialized")
    
    def create_execution_strategy(self, objectives: str, context: Optional[Dict[str, Any]] = None) -> ExecutionStrategy:
        """
        Create an execution strategy for given objectives.
        
        Args:
            objectives: The objectives to achieve
            context: Optional context information
            
        Returns:
            ExecutionStrategy instance
            
        Raises:
            WorkerError: If strategy creation fails
        """
        try:
            # Analyze objectives to determine approach
            analysis = self._analyze_objectives(objectives, context or {})
            
            # Create strategy
            strategy = ExecutionStrategy(
                strategy_id=str(uuid.uuid4()),
                objectives=objectives,
                approach=analysis['approach'],
                required_workers=analysis['required_workers'],
                task_breakdown=analysis['task_breakdown'],
                success_criteria=analysis['success_criteria'],
                estimated_duration=analysis.get('estimated_duration')
            )
            
            # Store strategy
            self.created_strategies[strategy.strategy_id] = strategy
            
            self.logger.info(f"Created execution strategy: {strategy.strategy_id}")
            return strategy
            
        except Exception as e:
            self.logger.error(f"Strategy creation failed: {e}")
            raise WorkerError(
                f"Failed to create execution strategy: {e}",
                worker_id=self.worker_id,
                context={'objectives': objectives, 'error': str(e)}
            )
    
    def create_new_worker(self, worker_spec: WorkerCreationSpec) -> Optional[str]:
        """
        Create a new worker based on specifications.
        
        Args:
            worker_spec: Specification for the new worker
            
        Returns:
            Worker ID if successful, None otherwise
            
        Raises:
            WorkerError: If worker creation fails
        """
        if len(self.managed_workers) >= self.worker_creation_limit:
            raise WorkerError(
                f"Worker creation limit reached: {self.worker_creation_limit}",
                worker_id=self.worker_id,
                context={'current_workers': len(self.managed_workers)}
            )
        
        if not self._is_connected:
            raise WorkerError(
                "Cannot create worker - not connected to server",
                worker_id=self.worker_id,
                context={'operation': 'create_new_worker'}
            )
        
        try:
            server = self.server_connection.server_instance
            worker_registry = server.get_worker_registry()
            
            # Create worker through server
            new_worker_id = worker_registry.create_specialized_worker(
                worker_type=worker_spec.worker_type,
                name=worker_spec.name,
                role=worker_spec.role,
                capabilities=worker_spec.capabilities,
                config=worker_spec.config,
                created_by=self.worker_id
            )
            
            if new_worker_id:
                # Track the created worker
                self.managed_workers[new_worker_id] = {
                    'worker_type': worker_spec.worker_type,
                    'name': worker_spec.name,
                    'role': worker_spec.role,
                    'created_at': datetime.now(),
                    'status': 'active',
                    'priority': worker_spec.priority,
                    'tasks_assigned': 0,
                    'last_communication': None
                }
                
                self.logger.info(f"Created new {worker_spec.worker_type.value} worker: {new_worker_id}")
                return new_worker_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Worker creation failed: {e}")
            raise WorkerError(
                f"Failed to create worker: {e}",
                worker_id=self.worker_id,
                context={'worker_spec': worker_spec.__dict__, 'error': str(e)}
            )
    
    def assign_task_to_executor(self, executor_id: str, task_description: str,
                              task_parameters: Optional[Dict[str, Any]] = None,
                              priority: int = 5) -> bool:
        """
        Assign a task to an executor worker.
        
        Args:
            executor_id: ID of the executor worker
            task_description: Description of the task
            task_parameters: Optional task parameters
            priority: Task priority (1-10)
            
        Returns:
            True if assignment was successful
        """
        # Verify executor exists and is managed by this planner
        if executor_id not in self.managed_workers:
            self.logger.warning(f"Executor {executor_id} not managed by this planner")
            return False
        
        worker_info = self.managed_workers[executor_id]
        if worker_info['worker_type'] != WorkerType.EXECUTOR:
            self.logger.error(f"Worker {executor_id} is not an executor")
            return False
        
        # Create task assignment
        assignment_id = str(uuid.uuid4())
        task_assignment = {
            'assignment_id': assignment_id,
            'executor_id': executor_id,
            'task_description': task_description,
            'task_parameters': task_parameters or {},
            'priority': priority,
            'assigned_at': datetime.now(),
            'status': 'assigned',
            'planner_id': self.worker_id
        }
        
        # Send task delegation message
        message = {
            'message_type': MessageType.TASK_DELEGATION.value,
            'assignment_id': assignment_id,
            'task_description': task_description,
            'task_parameters': task_parameters or {},
            'priority': priority,
            'assigned_by': self.worker_id,
            'assigned_at': datetime.now().isoformat(),
            'requires_response': True
        }
        
        success = self.send_message_to_worker(executor_id, message)
        
        if success:
            # Track assignment
            self.task_assignments[assignment_id] = task_assignment
            worker_info['tasks_assigned'] += 1
            worker_info['last_communication'] = datetime.now()
            
            self.logger.info(f"Assigned task to executor {executor_id}: {task_description}")
        
        return success
    
    def create_workflow_flowchart(self, objectives: str, strategy: Optional[ExecutionStrategy] = None) -> WorkerFlowchart:
        """
        Create a workflow flowchart for worker interactions.
        
        Args:
            objectives: The objectives to achieve
            strategy: Optional existing strategy to base flowchart on
            
        Returns:
            WorkerFlowchart instance
        """
        if not strategy:
            strategy = self.create_execution_strategy(objectives)
        
        # Design interaction patterns
        interaction_patterns = self._design_interaction_patterns(strategy)
        
        # Create execution order
        execution_order = self._create_execution_order(strategy, interaction_patterns)
        
        # Create flowchart
        flowchart = WorkerFlowchart(
            flowchart_id=str(uuid.uuid4()),
            objectives=objectives,
            planner_count=strategy.required_workers.get(WorkerType.PLANNER, 1),
            executor_count=strategy.required_workers.get(WorkerType.EXECUTOR, 1),
            verifier_count=strategy.required_workers.get(WorkerType.VERIFIER, 1),
            interaction_patterns=interaction_patterns,
            execution_order=execution_order,
            success_criteria=strategy.success_criteria,
            created_by=self.worker_id,
            created_at=datetime.now(),
            status="active"
        )
        
        # Store flowchart
        self.active_flowcharts[flowchart.flowchart_id] = flowchart
        
        self.logger.info(f"Created workflow flowchart: {flowchart.flowchart_id}")
        return flowchart
    
    def monitor_execution_progress(self) -> Dict[str, Any]:
        """
        Monitor progress of all managed workers and assignments.
        
        Returns:
            Dictionary containing progress information
        """
        progress = {
            'managed_workers': len(self.managed_workers),
            'active_assignments': len([a for a in self.task_assignments.values() if a['status'] in ['assigned', 'in_progress']]),
            'completed_assignments': len([a for a in self.task_assignments.values() if a['status'] == 'completed']),
            'failed_assignments': len([a for a in self.task_assignments.values() if a['status'] == 'failed']),
            'active_strategies': len(self.created_strategies),
            'active_flowcharts': len(self.active_flowcharts),
            'worker_status': {}
        }
        
        # Get status for each managed worker
        for worker_id, worker_info in self.managed_workers.items():
            progress['worker_status'][worker_id] = {
                'name': worker_info['name'],
                'type': worker_info['worker_type'].value,
                'status': worker_info['status'],
                'tasks_assigned': worker_info['tasks_assigned'],
                'last_communication': worker_info['last_communication'].isoformat() if worker_info['last_communication'] else None
            }
        
        return progress
    
    def request_worker_verification(self, verifier_id: str, output_to_verify: Any,
                                  verification_criteria: Optional[Dict[str, Any]] = None) -> bool:
        """
        Request verification from a verifier worker.
        
        Args:
            verifier_id: ID of the verifier worker
            output_to_verify: Output that needs verification
            verification_criteria: Optional verification criteria
            
        Returns:
            True if verification request was sent
        """
        # Verify verifier exists and is managed by this planner
        if verifier_id not in self.managed_workers:
            self.logger.warning(f"Verifier {verifier_id} not managed by this planner")
            return False
        
        worker_info = self.managed_workers[verifier_id]
        if worker_info['worker_type'] != WorkerType.VERIFIER:
            self.logger.error(f"Worker {verifier_id} is not a verifier")
            return False
        
        # Send verification request
        success = self.request_verification(verifier_id, output_to_verify, verification_criteria)
        
        if success:
            worker_info['last_communication'] = datetime.now()
        
        return success
    
    def get_planner_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for this planner.
        
        Returns:
            Dictionary containing planner statistics
        """
        base_stats = self.get_collaboration_statistics()
        
        planner_stats = {
            'strategies_created': len(self.created_strategies),
            'workers_managed': len(self.managed_workers),
            'tasks_assigned': len(self.task_assignments),
            'flowcharts_created': len(self.active_flowcharts),
            'worker_breakdown': {
                'planners': len([w for w in self.managed_workers.values() if w['worker_type'] == WorkerType.PLANNER]),
                'executors': len([w for w in self.managed_workers.values() if w['worker_type'] == WorkerType.EXECUTOR]),
                'verifiers': len([w for w in self.managed_workers.values() if w['worker_type'] == WorkerType.VERIFIER])
            }
        }
        
        return {**base_stats, **planner_stats}
    
    def _analyze_objectives(self, objectives: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze objectives to determine execution approach.
        
        Args:
            objectives: The objectives to analyze
            context: Additional context information
            
        Returns:
            Dictionary containing analysis results
        """
        # Simple analysis logic - can be enhanced with AI/ML
        analysis = {
            'approach': 'collaborative',
            'required_workers': {
                WorkerType.EXECUTOR: 1,
                WorkerType.VERIFIER: 1
            },
            'task_breakdown': [
                {
                    'task_id': str(uuid.uuid4()),
                    'description': f"Execute: {objectives}",
                    'worker_type': WorkerType.EXECUTOR,
                    'priority': 5,
                    'estimated_duration': 30
                }
            ],
            'success_criteria': {
                'completion_required': True,
                'quality_threshold': 0.8,
                'verification_required': True
            }
        }
        
        # Adjust based on complexity indicators
        if any(keyword in objectives.lower() for keyword in ['complex', 'multiple', 'various', 'several']):
            analysis['required_workers'][WorkerType.EXECUTOR] = 2
            analysis['approach'] = 'multi_executor'
        
        if any(keyword in objectives.lower() for keyword in ['critical', 'important', 'quality', 'accurate']):
            analysis['success_criteria']['quality_threshold'] = 0.9
            analysis['required_workers'][WorkerType.VERIFIER] = 1
        
        return analysis
    
    def _design_interaction_patterns(self, strategy: ExecutionStrategy) -> List[Dict[str, Any]]:
        """
        Design interaction patterns for a strategy.
        
        Args:
            strategy: The execution strategy
            
        Returns:
            List of interaction pattern dictionaries
        """
        patterns = []
        
        # Basic planner -> executor pattern
        patterns.append({
            'pattern_id': str(uuid.uuid4()),
            'from_worker_type': WorkerType.PLANNER.value,
            'to_worker_type': WorkerType.EXECUTOR.value,
            'interaction_type': 'task_delegation',
            'conditions': {'task_available': True},
            'parameters': {'priority_threshold': 3}
        })
        
        # Executor -> verifier pattern
        patterns.append({
            'pattern_id': str(uuid.uuid4()),
            'from_worker_type': WorkerType.EXECUTOR.value,
            'to_worker_type': WorkerType.VERIFIER.value,
            'interaction_type': 'verification_request',
            'conditions': {'output_ready': True},
            'parameters': {'quality_threshold': strategy.success_criteria.get('quality_threshold', 0.8)}
        })
        
        # Verifier -> planner pattern
        patterns.append({
            'pattern_id': str(uuid.uuid4()),
            'from_worker_type': WorkerType.VERIFIER.value,
            'to_worker_type': WorkerType.PLANNER.value,
            'interaction_type': 'result_report',
            'conditions': {'verification_complete': True},
            'parameters': {}
        })
        
        return patterns
    
    def _create_execution_order(self, strategy: ExecutionStrategy, 
                              interaction_patterns: List[Dict[str, Any]]) -> List[str]:
        """
        Create execution order based on strategy and patterns.
        
        Args:
            strategy: The execution strategy
            interaction_patterns: List of interaction patterns
            
        Returns:
            List of execution step identifiers
        """
        order = []
        
        # Add task breakdown steps
        for task in strategy.task_breakdown:
            order.append(f"task_{task['task_id']}")
        
        # Add verification steps
        if strategy.success_criteria.get('verification_required', False):
            order.append("verification_phase")
        
        # Add completion step
        order.append("completion_phase")
        
        return order
    
    def _setup_planner_message_handlers(self) -> None:
        """Setup planner-specific message handlers."""
        # Add planner-specific handlers to existing ones
        self.message_handlers[MessageType.RESULT_REPORT] = self._handle_planner_result_report
        self.message_handlers[MessageType.STATUS_UPDATE] = self._handle_planner_status_update
    
    def _handle_planner_result_report(self, message) -> None:
        """Handle result reports from managed workers."""
        from_worker_id = message.from_worker_id
        
        # Update assignment status if this is from a managed worker
        assignment_id = message.content.get('assignment_id')
        if assignment_id and assignment_id in self.task_assignments:
            assignment = self.task_assignments[assignment_id]
            assignment['status'] = 'completed'
            assignment['completed_at'] = datetime.now()
            assignment['result'] = message.content.get('result')
            
            self.logger.info(f"Task assignment {assignment_id} completed by {from_worker_id}")
        
        # Update worker info
        if from_worker_id in self.managed_workers:
            self.managed_workers[from_worker_id]['last_communication'] = datetime.now()
    
    def _handle_planner_status_update(self, message) -> None:
        """Handle status updates from managed workers."""
        from_worker_id = message.from_worker_id
        status = message.content.get('status', '')
        
        # Update worker status if this is from a managed worker
        if from_worker_id in self.managed_workers:
            self.managed_workers[from_worker_id]['status'] = status
            self.managed_workers[from_worker_id]['last_communication'] = datetime.now()
            
            self.logger.debug(f"Status update from managed worker {from_worker_id}: {status}")
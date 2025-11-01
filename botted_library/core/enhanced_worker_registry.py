"""
Enhanced Worker Registry for Collaborative Server

Extends the basic worker registry with specialized worker type support,
load balancing, and flowchart management capabilities.
"""

import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .worker_registry import WorkerRegistry
from .exceptions import WorkerError


class WorkerType(Enum):
    """Specialized worker types in the collaborative system"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


@dataclass
class WorkerCapability:
    """Represents a specific capability of a worker"""
    name: str
    level: int  # 1-10 proficiency level
    description: str
    last_used: Optional[datetime] = None


@dataclass
class WorkerFlowchart:
    """Represents a workflow pattern for worker interactions"""
    flowchart_id: str
    objectives: str
    planner_count: int
    executor_count: int
    verifier_count: int
    interaction_patterns: List[Dict[str, Any]]
    execution_order: List[str]
    success_criteria: Dict[str, Any]
    created_by: str
    created_at: datetime
    status: str = "draft"  # draft, active, completed, failed


@dataclass
class InteractionPattern:
    """Defines how workers interact with each other"""
    pattern_id: str
    from_worker_type: WorkerType
    to_worker_type: WorkerType
    interaction_type: str  # DELEGATE, VERIFY, COLLABORATE, REPORT
    conditions: Dict[str, Any]
    parameters: Dict[str, Any]


class EnhancedWorkerRegistry(WorkerRegistry):
    """
    Enhanced worker registry with specialized worker type support.
    
    Extends the basic WorkerRegistry with:
    - Worker type specialization (Planner, Executor, Verifier)
    - Advanced capability matching and load balancing
    - Flowchart creation and management
    - Performance tracking and optimization
    """
    
    def __new__(cls, server_instance=None):
        """Override singleton behavior to allow multiple instances for testing"""
        # Don't use singleton pattern for enhanced registry
        return object.__new__(cls)
    
    def __init__(self, server_instance=None):
        """
        Initialize the enhanced worker registry.
        
        Args:
            server_instance: Reference to the collaborative server
        """
        # Initialize base registry attributes manually to avoid singleton issues
        self.active_workers: Dict[str, Dict[str, Any]] = {}
        self.collaboration_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._initialized = True
        
        self.server_instance = server_instance
        
        # Enhanced registry data structures
        self.worker_types: Dict[str, WorkerType] = {}
        self.worker_capabilities: Dict[str, List[WorkerCapability]] = {}
        self.worker_performance: Dict[str, Dict[str, Any]] = {}
        self.load_balancing_stats: Dict[str, Dict[str, Any]] = {}
        
        # Flowchart management
        self.flowcharts: Dict[str, WorkerFlowchart] = {}
        self.active_flowcharts: Set[str] = set()
        
        # Enhanced threading support
        self._enhanced_lock = threading.RLock()
        
        # Performance tracking
        self.performance_metrics = {
            'total_tasks_assigned': 0,
            'successful_assignments': 0,
            'failed_assignments': 0,
            'average_response_time': 0.0
        }
    
    def register_specialized_worker(self, worker_id: str, worker_info: Dict[str, Any]) -> str:
        """
        Register a worker with specialized type and capabilities.
        
        Args:
            worker_id: Unique identifier for the worker
            worker_info: Enhanced worker information including type and capabilities
            
        Returns:
            Registration confirmation ID
            
        Raises:
            WorkerError: If registration fails or invalid worker type
        """
        with self._enhanced_lock:
            try:
                # Validate worker type
                worker_type_str = worker_info.get('worker_type', 'executor')
                try:
                    worker_type = WorkerType(worker_type_str.lower())
                except ValueError:
                    raise WorkerError(
                        f"Invalid worker type: {worker_type_str}. Must be one of: {[t.value for t in WorkerType]}",
                        worker_id=worker_id,
                        context={'operation': 'register_specialized_worker'}
                    )
                
                # Register with base registry first
                self.register_worker(
                    worker_id=worker_id,
                    worker_name=worker_info.get('name', f'Worker-{worker_id[:8]}'),
                    role=worker_info.get('role', worker_type.value.title()),
                    job_description=worker_info.get('job_description', f'{worker_type.value.title()} worker'),
                    capabilities=worker_info.get('capabilities', []),
                    worker_instance=worker_info.get('worker_instance')
                )
                
                # Store specialized information
                self.worker_types[worker_id] = worker_type
                
                # Process enhanced capabilities
                capabilities = worker_info.get('enhanced_capabilities', [])
                self.worker_capabilities[worker_id] = []
                
                for cap in capabilities:
                    if isinstance(cap, dict):
                        capability = WorkerCapability(
                            name=cap.get('name', ''),
                            level=cap.get('level', 5),
                            description=cap.get('description', ''),
                            last_used=None
                        )
                        self.worker_capabilities[worker_id].append(capability)
                
                # Initialize performance tracking
                self.worker_performance[worker_id] = {
                    'tasks_completed': 0,
                    'success_rate': 1.0,
                    'average_completion_time': 0.0,
                    'last_active': datetime.now(),
                    'specialization_score': self._calculate_specialization_score(worker_type, capabilities)
                }
                
                # Initialize load balancing stats
                self.load_balancing_stats[worker_id] = {
                    'current_load': 0,
                    'max_concurrent_tasks': worker_info.get('max_concurrent_tasks', 3),
                    'priority_score': self._calculate_priority_score(worker_type, capabilities),
                    'last_assigned': None
                }
                
                registration_id = str(uuid.uuid4())
                
                # Log registration
                if hasattr(self, 'logger'):
                    self.logger.info(f"Specialized worker registered: {worker_id} ({worker_type.value})")
                
                return registration_id
                
            except Exception as e:
                raise WorkerError(
                    f"Specialized worker registration failed: {e}",
                    worker_id=worker_id,
                    context={'operation': 'register_specialized_worker', 'error': str(e)}
                )
    
    def find_workers_by_type(self, worker_type: WorkerType, 
                           available_only: bool = True) -> List[Dict[str, Any]]:
        """
        Find all workers of a specific type.
        
        Args:
            worker_type: Type of workers to find
            available_only: If True, only return workers with available capacity
            
        Returns:
            List of worker information dictionaries
        """
        with self._enhanced_lock:
            matching_workers = []
            
            for worker_id, registered_type in self.worker_types.items():
                if registered_type == worker_type:
                    # Check availability if requested
                    if available_only:
                        load_stats = self.load_balancing_stats.get(worker_id, {})
                        current_load = load_stats.get('current_load', 0)
                        max_load = load_stats.get('max_concurrent_tasks', 3)
                        
                        if current_load >= max_load:
                            continue  # Worker is at capacity
                    
                    # Get worker info from base registry
                    worker_info = self.active_workers.get(worker_id)
                    if worker_info:
                        # Enhance with specialized information
                        enhanced_info = worker_info.copy()
                        enhanced_info.update({
                            'worker_type': registered_type.value,
                            'capabilities': self.worker_capabilities.get(worker_id, []),
                            'performance': self.worker_performance.get(worker_id, {}),
                            'load_stats': self.load_balancing_stats.get(worker_id, {})
                        })
                        matching_workers.append(enhanced_info)
            
            # Sort by priority score (highest first)
            matching_workers.sort(
                key=lambda w: w.get('load_stats', {}).get('priority_score', 0),
                reverse=True
            )
            
            return matching_workers
    
    def get_load_balanced_worker(self, worker_type: WorkerType, 
                               task_requirements: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get the best available worker for a task using load balancing.
        
        Args:
            worker_type: Type of worker needed
            task_requirements: Requirements for the task (capabilities, priority, etc.)
            
        Returns:
            Best available worker or None if no suitable worker found
        """
        with self._enhanced_lock:
            available_workers = self.find_workers_by_type(worker_type, available_only=True)
            
            if not available_workers:
                return None
            
            # Score workers based on task requirements
            scored_workers = []
            
            for worker in available_workers:
                score = self._calculate_worker_task_score(worker, task_requirements)
                scored_workers.append((score, worker))
            
            # Sort by score (highest first)
            scored_workers.sort(key=lambda x: x[0], reverse=True)
            
            # Return the best worker
            if scored_workers:
                best_worker = scored_workers[0][1]
                
                # Update load balancing stats
                worker_id = best_worker['worker_id']
                if worker_id in self.load_balancing_stats:
                    self.load_balancing_stats[worker_id]['current_load'] += 1
                    self.load_balancing_stats[worker_id]['last_assigned'] = datetime.now()
                
                return best_worker
            
            return None
    
    def create_worker_flowchart(self, objectives: str, created_by: str,
                              planner_count: int = 1, executor_count: int = 2,
                              verifier_count: int = 1) -> WorkerFlowchart:
        """
        Create a new worker flowchart for task execution.
        
        Args:
            objectives: Description of what needs to be accomplished
            created_by: ID of the worker/user creating the flowchart
            planner_count: Number of planner workers needed
            executor_count: Number of executor workers needed
            verifier_count: Number of verifier workers needed
            
        Returns:
            Created WorkerFlowchart instance
        """
        with self._enhanced_lock:
            flowchart_id = str(uuid.uuid4())
            
            # Generate interaction patterns based on worker counts
            interaction_patterns = self._generate_interaction_patterns(
                planner_count, executor_count, verifier_count
            )
            
            # Generate execution order
            execution_order = self._generate_execution_order(
                planner_count, executor_count, verifier_count
            )
            
            # Define success criteria
            success_criteria = {
                'all_workers_created': True,
                'tasks_completed': True,
                'quality_verified': True,
                'objectives_met': True
            }
            
            flowchart = WorkerFlowchart(
                flowchart_id=flowchart_id,
                objectives=objectives,
                planner_count=planner_count,
                executor_count=executor_count,
                verifier_count=verifier_count,
                interaction_patterns=interaction_patterns,
                execution_order=execution_order,
                success_criteria=success_criteria,
                created_by=created_by,
                created_at=datetime.now()
            )
            
            self.flowcharts[flowchart_id] = flowchart
            
            return flowchart
    
    def create_specialized_worker(self, worker_type: WorkerType, name: str, role: str,
                                capabilities: List[str], config: Dict[str, Any],
                                created_by: str) -> Optional[str]:
        """
        Create a new specialized worker instance.
        
        Args:
            worker_type: Type of worker to create
            name: Name for the new worker
            role: Role/title for the worker
            capabilities: List of capability names
            config: Configuration parameters
            created_by: ID of the worker/user creating this worker
            
        Returns:
            Worker ID if successful, None otherwise
        """
        try:
            # Import specialized worker classes
            from .planner_worker import PlannerWorker
            from .executor_worker import ExecutorWorker
            from .verifier_worker import VerifierWorker
            from .enhanced_worker import ServerConnection
            
            # Generate worker ID
            worker_id = str(uuid.uuid4())
            
            # Create server connection if server instance is available
            server_connection = None
            if self.server_instance:
                server_connection = ServerConnection(
                    server_instance=self.server_instance,
                    worker_id=worker_id,
                    connection_id=str(uuid.uuid4()),
                    connected_at=datetime.now(),
                    is_active=True
                )
            
            # Get required components (simplified for now)
            # In a real implementation, these would be properly initialized
            memory_system = None
            knowledge_validator = None
            browser_controller = None
            task_executor = None
            
            # Create the appropriate worker type
            if worker_type == WorkerType.PLANNER:
                worker = PlannerWorker(
                    name=name,
                    role=role,
                    memory_system=memory_system,
                    knowledge_validator=knowledge_validator,
                    browser_controller=browser_controller,
                    task_executor=task_executor,
                    server_connection=server_connection,
                    worker_id=worker_id,
                    config=config
                )
            elif worker_type == WorkerType.EXECUTOR:
                worker = ExecutorWorker(
                    name=name,
                    role=role,
                    memory_system=memory_system,
                    knowledge_validator=knowledge_validator,
                    browser_controller=browser_controller,
                    task_executor=task_executor,
                    server_connection=server_connection,
                    worker_id=worker_id,
                    config=config
                )
            elif worker_type == WorkerType.VERIFIER:
                worker = VerifierWorker(
                    name=name,
                    role=role,
                    memory_system=memory_system,
                    knowledge_validator=knowledge_validator,
                    browser_controller=browser_controller,
                    task_executor=task_executor,
                    server_connection=server_connection,
                    worker_id=worker_id,
                    config=config
                )
            else:
                raise WorkerError(f"Unknown worker type: {worker_type}")
            
            # Register the worker
            worker_info = {
                'name': name,
                'role': role,
                'worker_type': worker_type.value,
                'capabilities': capabilities,
                'enhanced_capabilities': [
                    {'name': cap, 'level': 7, 'description': f'{cap} capability'}
                    for cap in capabilities
                ],
                'worker_instance': worker,
                'max_concurrent_tasks': config.get('max_concurrent_tasks', 3),
                'created_by': created_by
            }
            
            self.register_specialized_worker(worker_id, worker_info)
            
            return worker_id
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Failed to create specialized worker: {e}")
            return None

    def activate_flowchart(self, flowchart_id: str) -> bool:
        """
        Activate a flowchart for execution.
        
        Args:
            flowchart_id: ID of the flowchart to activate
            
        Returns:
            True if activation successful
        """
        with self._enhanced_lock:
            if flowchart_id not in self.flowcharts:
                return False
            
            flowchart = self.flowcharts[flowchart_id]
            flowchart.status = "active"
            self.active_flowcharts.add(flowchart_id)
            
            return True
    
    def complete_task_assignment(self, worker_id: str, success: bool, 
                               completion_time: float) -> None:
        """
        Record completion of a task assignment for performance tracking.
        
        Args:
            worker_id: ID of the worker who completed the task
            success: Whether the task was completed successfully
            completion_time: Time taken to complete the task in seconds
        """
        with self._enhanced_lock:
            # Update load balancing stats
            if worker_id in self.load_balancing_stats:
                self.load_balancing_stats[worker_id]['current_load'] = max(
                    0, self.load_balancing_stats[worker_id]['current_load'] - 1
                )
            
            # Update performance metrics
            if worker_id in self.worker_performance:
                perf = self.worker_performance[worker_id]
                perf['tasks_completed'] += 1
                perf['last_active'] = datetime.now()
                
                # Update success rate (exponential moving average)
                current_rate = perf['success_rate']
                perf['success_rate'] = 0.9 * current_rate + 0.1 * (1.0 if success else 0.0)
                
                # Update average completion time (exponential moving average)
                current_avg = perf['average_completion_time']
                perf['average_completion_time'] = 0.9 * current_avg + 0.1 * completion_time
            
            # Update global metrics
            self.performance_metrics['total_tasks_assigned'] += 1
            if success:
                self.performance_metrics['successful_assignments'] += 1
            else:
                self.performance_metrics['failed_assignments'] += 1
    
    def cleanup_inactive_workers(self, inactive_threshold_minutes: int = 30) -> int:
        """
        Remove workers that have been inactive for too long.
        
        Args:
            inactive_threshold_minutes: Minutes of inactivity before cleanup
            
        Returns:
            Number of workers cleaned up
        """
        with self._enhanced_lock:
            threshold = datetime.now() - timedelta(minutes=inactive_threshold_minutes)
            inactive_workers = []
            
            for worker_id, perf in self.worker_performance.items():
                if perf.get('last_active', datetime.now()) < threshold:
                    inactive_workers.append(worker_id)
            
            # Remove inactive workers
            for worker_id in inactive_workers:
                self.unregister_worker(worker_id)
                
                # Clean up enhanced data structures
                self.worker_types.pop(worker_id, None)
                self.worker_capabilities.pop(worker_id, None)
                self.worker_performance.pop(worker_id, None)
                self.load_balancing_stats.pop(worker_id, None)
            
            return len(inactive_workers)
    
    def get_registry_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive registry statistics.
        
        Returns:
            Dictionary containing detailed registry statistics
        """
        with self._enhanced_lock:
            # Count workers by type
            type_counts = {}
            for worker_type in self.worker_types.values():
                type_counts[worker_type.value] = type_counts.get(worker_type.value, 0) + 1
            
            # Calculate average performance metrics
            total_workers = len(self.worker_performance)
            avg_success_rate = 0.0
            avg_completion_time = 0.0
            
            if total_workers > 0:
                avg_success_rate = sum(
                    perf['success_rate'] for perf in self.worker_performance.values()
                ) / total_workers
                
                avg_completion_time = sum(
                    perf['average_completion_time'] for perf in self.worker_performance.values()
                ) / total_workers
            
            return {
                'total_workers': total_workers,
                'workers_by_type': type_counts,
                'active_flowcharts': len(self.active_flowcharts),
                'total_flowcharts': len(self.flowcharts),
                'performance_metrics': {
                    **self.performance_metrics,
                    'average_success_rate': avg_success_rate,
                    'average_completion_time': avg_completion_time
                },
                'load_balancing': {
                    'total_current_load': sum(
                        stats['current_load'] for stats in self.load_balancing_stats.values()
                    ),
                    'workers_at_capacity': sum(
                        1 for stats in self.load_balancing_stats.values()
                        if stats['current_load'] >= stats['max_concurrent_tasks']
                    )
                }
            }
    
    def shutdown(self) -> None:
        """Shutdown the enhanced worker registry."""
        with self._enhanced_lock:
            # Clear enhanced data structures
            self.worker_types.clear()
            self.worker_capabilities.clear()
            self.worker_performance.clear()
            self.load_balancing_stats.clear()
            self.flowcharts.clear()
            self.active_flowcharts.clear()
            
            # Call parent shutdown if available
            if hasattr(super(), 'shutdown'):
                super().shutdown()
    
    def _calculate_specialization_score(self, worker_type: WorkerType, 
                                      capabilities: List[Dict[str, Any]]) -> float:
        """Calculate a specialization score for a worker."""
        base_score = 5.0  # Base score for having a specialized type
        
        # Add points for relevant capabilities
        capability_bonus = min(len(capabilities) * 0.5, 3.0)
        
        # Type-specific bonuses
        type_bonus = {
            WorkerType.PLANNER: 1.0,
            WorkerType.EXECUTOR: 0.5,
            WorkerType.VERIFIER: 1.5
        }.get(worker_type, 0.0)
        
        return base_score + capability_bonus + type_bonus
    
    def _calculate_priority_score(self, worker_type: WorkerType, 
                                capabilities: List[Dict[str, Any]]) -> float:
        """Calculate a priority score for load balancing."""
        # Base priority by type
        type_priority = {
            WorkerType.PLANNER: 8.0,
            WorkerType.EXECUTOR: 6.0,
            WorkerType.VERIFIER: 7.0
        }.get(worker_type, 5.0)
        
        # Capability bonus
        capability_bonus = min(len(capabilities) * 0.3, 2.0)
        
        return type_priority + capability_bonus
    
    def _calculate_worker_task_score(self, worker: Dict[str, Any], 
                                   task_requirements: Dict[str, Any]) -> float:
        """Calculate how well a worker matches task requirements."""
        score = 0.0
        
        # Base score from priority
        score += worker.get('load_stats', {}).get('priority_score', 0.0)
        
        # Performance bonus
        performance = worker.get('performance', {})
        score += performance.get('success_rate', 0.5) * 2.0
        
        # Load penalty (prefer less loaded workers)
        load_stats = worker.get('load_stats', {})
        current_load = load_stats.get('current_load', 0)
        max_load = load_stats.get('max_concurrent_tasks', 3)
        load_ratio = current_load / max_load if max_load > 0 else 0
        score -= load_ratio * 3.0
        
        # Capability matching
        required_capabilities = task_requirements.get('capabilities', [])
        worker_capabilities = [cap.name for cap in worker.get('capabilities', [])]
        
        capability_matches = sum(
            1 for req_cap in required_capabilities
            if req_cap in worker_capabilities
        )
        score += capability_matches * 1.5
        
        return max(score, 0.0)
    
    def _generate_interaction_patterns(self, planner_count: int, 
                                     executor_count: int, 
                                     verifier_count: int) -> List[Dict[str, Any]]:
        """Generate interaction patterns for a flowchart."""
        patterns = []
        
        # Planner -> Executor delegation
        patterns.append({
            'from_type': WorkerType.PLANNER.value,
            'to_type': WorkerType.EXECUTOR.value,
            'interaction': 'DELEGATE',
            'description': 'Planners delegate tasks to executors'
        })
        
        # Executor -> Verifier verification
        patterns.append({
            'from_type': WorkerType.EXECUTOR.value,
            'to_type': WorkerType.VERIFIER.value,
            'interaction': 'VERIFY',
            'description': 'Executors request verification from verifiers'
        })
        
        # Verifier -> Planner reporting
        patterns.append({
            'from_type': WorkerType.VERIFIER.value,
            'to_type': WorkerType.PLANNER.value,
            'interaction': 'REPORT',
            'description': 'Verifiers report results back to planners'
        })
        
        return patterns
    
    def _generate_execution_order(self, planner_count: int, 
                                executor_count: int, 
                                verifier_count: int) -> List[str]:
        """Generate execution order for a flowchart."""
        order = []
        
        # Create planners first
        for i in range(planner_count):
            order.append(f"create_planner_{i+1}")
        
        # Create executors
        for i in range(executor_count):
            order.append(f"create_executor_{i+1}")
        
        # Create verifiers
        for i in range(verifier_count):
            order.append(f"create_verifier_{i+1}")
        
        # Execute workflow
        order.extend([
            "initialize_collaboration",
            "execute_tasks",
            "verify_results",
            "complete_objectives"
        ])
        
        return order
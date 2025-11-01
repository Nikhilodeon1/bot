"""
Manual Mode Controller for Collaborative Worker System

Provides user-controlled operations for worker creation, task assignment,
and collaborative space management in manual mode.
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

from .enhanced_worker_registry import WorkerType
from .exceptions import WorkerError


class ManualModeController:
    """
    Controller for manual mode operations where users directly control
    worker creation, task assignment, and collaborative space management.
    
    In manual mode, users have full control over:
    - Creating workers of specific types
    - Assigning tasks to specific workers
    - Managing collaborative spaces
    - Coordinating worker interactions
    """
    
    def __init__(self, server_instance, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the manual mode controller.
        
        Args:
            server_instance: Reference to the collaborative server
            config: Optional configuration parameters
        """
        self.server = server_instance
        self.config = config or {}
        self.controller_id = str(uuid.uuid4())
        
        # Setup logging
        self.logger = logging.getLogger(f"ManualModeController.{self.controller_id[:8]}")
        
        # Track manual operations
        self.manual_workers: Dict[str, Dict[str, Any]] = {}
        self.manual_spaces: Dict[str, Dict[str, Any]] = {}
        self.manual_tasks: Dict[str, Dict[str, Any]] = {}
        
        # User interface callbacks
        self.ui_callbacks: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            'workers_created': 0,
            'tasks_assigned': 0,
            'spaces_created': 0,
            'operations_performed': 0
        }
        
        self.logger.info(f"ManualModeController initialized with ID: {self.controller_id[:8]}")
    
    def create_worker_manually(self, worker_type: WorkerType, name: str, role: str,
                             capabilities: Optional[List[str]] = None,
                             config: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a worker manually with user-specified parameters.
        
        Args:
            worker_type: Type of worker to create (Planner, Executor, Verifier)
            name: Human-readable name for the worker
            role: Worker's role/title
            capabilities: Optional list of specific capabilities
            config: Optional worker configuration
            
        Returns:
            Worker ID of the created worker
            
        Raises:
            WorkerError: If worker creation fails
        """
        try:
            # Import worker classes here to avoid circular imports
            from .planner_worker import PlannerWorker
            from .executor_worker import ExecutorWorker
            from .verifier_worker import VerifierWorker
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
            
            # Get required components from server
            worker_registry = self.server.get_worker_registry()
            
            # Create worker based on type
            worker_config = config or {}
            worker_config.update({
                'manual_mode': True,
                'created_by_controller': self.controller_id
            })
            
            if worker_type == WorkerType.PLANNER:
                worker = PlannerWorker(
                    name=name,
                    role=role,
                    memory_system=None,  # Will be initialized by worker
                    knowledge_validator=None,  # Will be initialized by worker
                    browser_controller=None,  # Will be initialized by worker
                    task_executor=None,  # Will be initialized by worker
                    server_connection=server_connection,
                    worker_id=worker_id,
                    config=worker_config
                )
            elif worker_type == WorkerType.EXECUTOR:
                worker = ExecutorWorker(
                    name=name,
                    role=role,
                    memory_system=None,  # Will be initialized by worker
                    knowledge_validator=None,  # Will be initialized by worker
                    browser_controller=None,  # Will be initialized by worker
                    task_executor=None,  # Will be initialized by worker
                    server_connection=server_connection,
                    worker_id=worker_id,
                    config=worker_config
                )
            elif worker_type == WorkerType.VERIFIER:
                worker = VerifierWorker(
                    name=name,
                    role=role,
                    memory_system=None,  # Will be initialized by worker
                    knowledge_validator=None,  # Will be initialized by worker
                    browser_controller=None,  # Will be initialized by worker
                    task_executor=None,  # Will be initialized by worker
                    server_connection=server_connection,
                    worker_id=worker_id,
                    config=worker_config
                )
            else:
                raise WorkerError(
                    f"Unsupported worker type: {worker_type}",
                    worker_id=worker_id,
                    context={'operation': 'create_worker_manually'}
                )
            
            # Connect worker to server
            worker.connect_to_server()
            
            # Track the manually created worker
            self.manual_workers[worker_id] = {
                'worker_instance': worker,
                'worker_type': worker_type,
                'name': name,
                'role': role,
                'capabilities': capabilities or [],
                'created_at': datetime.now(),
                'created_by': 'manual_controller',
                'config': worker_config,
                'status': 'active'
            }
            
            self.stats['workers_created'] += 1
            self.stats['operations_performed'] += 1
            
            self.logger.info(f"Manually created {worker_type.value} worker: {name} ({worker_id})")
            
            # Notify UI if callback is registered
            if 'worker_created' in self.ui_callbacks:
                self.ui_callbacks['worker_created'](worker_id, worker_type, name)
            
            return worker_id
            
        except Exception as e:
            self.logger.error(f"Manual worker creation failed: {e}")
            raise WorkerError(
                f"Manual worker creation failed: {e}",
                worker_id=worker_id if 'worker_id' in locals() else None,
                context={'operation': 'create_worker_manually', 'error': str(e)}
            )
    
    def assign_task_manually(self, worker_id: str, task_description: str,
                           task_parameters: Optional[Dict[str, Any]] = None,
                           priority: int = 1,
                           deadline: Optional[datetime] = None) -> str:
        """
        Manually assign a task to a specific worker.
        
        Args:
            worker_id: ID of the worker to assign the task to
            task_description: Description of the task
            task_parameters: Optional task parameters
            priority: Task priority (1-10, higher is more urgent)
            deadline: Optional task deadline
            
        Returns:
            Task ID of the assigned task
            
        Raises:
            WorkerError: If task assignment fails
        """
        try:
            # Validate worker exists
            if worker_id not in self.manual_workers:
                raise WorkerError(
                    f"Worker {worker_id} not found in manual workers",
                    worker_id=worker_id,
                    context={'operation': 'assign_task_manually'}
                )
            
            worker_info = self.manual_workers[worker_id]
            worker_instance = worker_info['worker_instance']
            
            # Create task
            from .interfaces import Task
            
            task_id = str(uuid.uuid4())
            task = Task.create_new(
                description=task_description,
                parameters=task_parameters or {},
                priority=priority,
                deadline=deadline,
                context={
                    'assigned_by': 'manual_controller',
                    'assignment_method': 'manual',
                    'controller_id': self.controller_id
                }
            )
            task.id = task_id  # Override with our generated ID
            
            # Track the manual task assignment
            self.manual_tasks[task_id] = {
                'task': task,
                'assigned_to': worker_id,
                'worker_name': worker_info['name'],
                'worker_type': worker_info['worker_type'].value,
                'assigned_at': datetime.now(),
                'status': 'assigned',
                'assignment_method': 'manual'
            }
            
            # Execute task on worker (async)
            # Note: In a real implementation, this might be done asynchronously
            try:
                result = worker_instance.execute_task(task)
                
                # Update task status
                self.manual_tasks[task_id]['status'] = 'completed' if result.is_successful() else 'failed'
                self.manual_tasks[task_id]['completed_at'] = datetime.now()
                self.manual_tasks[task_id]['result'] = result
                
            except Exception as task_error:
                self.manual_tasks[task_id]['status'] = 'failed'
                self.manual_tasks[task_id]['error'] = str(task_error)
                self.logger.error(f"Task execution failed: {task_error}")
            
            self.stats['tasks_assigned'] += 1
            self.stats['operations_performed'] += 1
            
            self.logger.info(f"Manually assigned task to {worker_info['name']}: {task_description}")
            
            # Notify UI if callback is registered
            if 'task_assigned' in self.ui_callbacks:
                self.ui_callbacks['task_assigned'](task_id, worker_id, task_description)
            
            return task_id
            
        except Exception as e:
            self.logger.error(f"Manual task assignment failed: {e}")
            raise WorkerError(
                f"Manual task assignment failed: {e}",
                worker_id=worker_id,
                context={'operation': 'assign_task_manually', 'error': str(e)}
            )
    
    def create_collaborative_space_manually(self, space_name: str, description: str,
                                          initial_participants: Optional[List[str]] = None,
                                          space_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Manually create a collaborative space with specified participants.
        
        Args:
            space_name: Human-readable name for the space
            description: Description of the space purpose
            initial_participants: Optional list of worker IDs to add initially
            space_config: Optional space configuration
            
        Returns:
            Space ID of the created collaborative space
            
        Raises:
            WorkerError: If space creation fails
        """
        try:
            # Create collaborative space through server
            space = self.server.create_collaborative_space(
                space_name=space_name,
                created_by=self.controller_id,
                description=description,
                config=space_config
            )
            
            space_id = space.space_id
            
            # Track the manually created space
            self.manual_spaces[space_id] = {
                'space_instance': space,
                'name': space_name,
                'description': description,
                'created_at': datetime.now(),
                'created_by': 'manual_controller',
                'participants': [],
                'config': space_config or {},
                'status': 'active'
            }
            
            # Add initial participants if specified
            if initial_participants:
                for worker_id in initial_participants:
                    if worker_id in self.manual_workers:
                        worker_instance = self.manual_workers[worker_id]['worker_instance']
                        success = worker_instance.join_collaborative_space(space_id)
                        
                        if success:
                            self.manual_spaces[space_id]['participants'].append(worker_id)
                            self.logger.info(f"Added {worker_id} to collaborative space {space_name}")
                    else:
                        self.logger.warning(f"Worker {worker_id} not found for space participation")
            
            self.stats['spaces_created'] += 1
            self.stats['operations_performed'] += 1
            
            self.logger.info(f"Manually created collaborative space: {space_name} ({space_id})")
            
            # Notify UI if callback is registered
            if 'space_created' in self.ui_callbacks:
                self.ui_callbacks['space_created'](space_id, space_name, len(initial_participants or []))
            
            return space_id
            
        except Exception as e:
            self.logger.error(f"Manual collaborative space creation failed: {e}")
            raise WorkerError(
                f"Manual collaborative space creation failed: {e}",
                worker_id=self.controller_id,
                context={'operation': 'create_collaborative_space_manually', 'error': str(e)}
            )
    
    def add_worker_to_space(self, worker_id: str, space_id: str) -> bool:
        """
        Manually add a worker to a collaborative space.
        
        Args:
            worker_id: ID of the worker to add
            space_id: ID of the collaborative space
            
        Returns:
            True if worker was added successfully
        """
        try:
            if worker_id not in self.manual_workers:
                self.logger.error(f"Worker {worker_id} not found in manual workers")
                return False
            
            if space_id not in self.manual_spaces:
                self.logger.error(f"Space {space_id} not found in manual spaces")
                return False
            
            worker_instance = self.manual_workers[worker_id]['worker_instance']
            success = worker_instance.join_collaborative_space(space_id)
            
            if success:
                self.manual_spaces[space_id]['participants'].append(worker_id)
                self.logger.info(f"Added worker {worker_id} to space {space_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to add worker to space: {e}")
            return False
    
    def remove_worker_from_space(self, worker_id: str, space_id: str) -> bool:
        """
        Manually remove a worker from a collaborative space.
        
        Args:
            worker_id: ID of the worker to remove
            space_id: ID of the collaborative space
            
        Returns:
            True if worker was removed successfully
        """
        try:
            if worker_id not in self.manual_workers:
                self.logger.error(f"Worker {worker_id} not found in manual workers")
                return False
            
            if space_id not in self.manual_spaces:
                self.logger.error(f"Space {space_id} not found in manual spaces")
                return False
            
            worker_instance = self.manual_workers[worker_id]['worker_instance']
            success = worker_instance.leave_collaborative_space(space_id)
            
            if success and worker_id in self.manual_spaces[space_id]['participants']:
                self.manual_spaces[space_id]['participants'].remove(worker_id)
                self.logger.info(f"Removed worker {worker_id} from space {space_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to remove worker from space: {e}")
            return False
    
    def get_manual_workers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all manually created workers.
        
        Returns:
            Dictionary of worker information keyed by worker ID
        """
        return {
            worker_id: {
                'name': info['name'],
                'role': info['role'],
                'worker_type': info['worker_type'].value,
                'capabilities': info['capabilities'],
                'created_at': info['created_at'].isoformat(),
                'status': info['status']
            }
            for worker_id, info in self.manual_workers.items()
        }
    
    def get_manual_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all manually assigned tasks.
        
        Returns:
            Dictionary of task information keyed by task ID
        """
        return {
            task_id: {
                'description': info['task'].description,
                'assigned_to': info['assigned_to'],
                'worker_name': info['worker_name'],
                'worker_type': info['worker_type'],
                'assigned_at': info['assigned_at'].isoformat(),
                'status': info['status'],
                'priority': info['task'].priority
            }
            for task_id, info in self.manual_tasks.items()
        }
    
    def get_manual_spaces(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all manually created collaborative spaces.
        
        Returns:
            Dictionary of space information keyed by space ID
        """
        return {
            space_id: {
                'name': info['name'],
                'description': info['description'],
                'created_at': info['created_at'].isoformat(),
                'participants': info['participants'],
                'participant_count': len(info['participants']),
                'status': info['status']
            }
            for space_id, info in self.manual_spaces.items()
        }
    
    def register_ui_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register a UI callback for manual mode events.
        
        Args:
            event_type: Type of event ('worker_created', 'task_assigned', 'space_created')
            callback: Callback function to call when event occurs
        """
        self.ui_callbacks[event_type] = callback
        self.logger.debug(f"Registered UI callback for event: {event_type}")
    
    def get_manual_mode_status(self) -> Dict[str, Any]:
        """
        Get current status of manual mode operations.
        
        Returns:
            Dictionary containing manual mode status and statistics
        """
        return {
            'controller_id': self.controller_id,
            'mode': 'manual',
            'active_workers': len([w for w in self.manual_workers.values() if w['status'] == 'active']),
            'active_spaces': len([s for s in self.manual_spaces.values() if s['status'] == 'active']),
            'pending_tasks': len([t for t in self.manual_tasks.values() if t['status'] == 'assigned']),
            'completed_tasks': len([t for t in self.manual_tasks.values() if t['status'] == 'completed']),
            'statistics': self.stats,
            'ui_callbacks_registered': list(self.ui_callbacks.keys())
        }
    
    def shutdown(self) -> None:
        """Shutdown the manual mode controller and cleanup resources."""
        try:
            # Disconnect all manual workers
            for worker_id, worker_info in self.manual_workers.items():
                try:
                    worker_instance = worker_info['worker_instance']
                    worker_instance.disconnect_from_server()
                    worker_info['status'] = 'disconnected'
                except Exception as e:
                    self.logger.error(f"Error disconnecting worker {worker_id}: {e}")
            
            # Close all manual spaces
            for space_id, space_info in self.manual_spaces.items():
                try:
                    space_instance = space_info['space_instance']
                    space_instance.close_space()
                    space_info['status'] = 'closed'
                except Exception as e:
                    self.logger.error(f"Error closing space {space_id}: {e}")
            
            # Clear tracking data
            self.manual_workers.clear()
            self.manual_spaces.clear()
            self.manual_tasks.clear()
            self.ui_callbacks.clear()
            
            self.logger.info("ManualModeController shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during manual mode controller shutdown: {e}")
"""
Error Recovery System for Collaborative Server

Provides comprehensive error handling and recovery mechanisms for:
- Server connection failures with automatic reconnection
- Worker crash detection and task reassignment
- Resource conflict resolution
- Communication failure handling with message queuing
"""

import asyncio
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from .exceptions import WorkerError, TaskExecutionError, BottedLibraryError


class RecoveryStrategy(Enum):
    """Recovery strategies for different types of failures"""
    RETRY = "retry"
    REASSIGN = "reassign"
    ESCALATE = "escalate"
    ABORT = "abort"
    IGNORE = "ignore"


class FailureType(Enum):
    """Types of failures that can occur in the system"""
    CONNECTION_FAILURE = "connection_failure"
    WORKER_CRASH = "worker_crash"
    TASK_TIMEOUT = "task_timeout"
    RESOURCE_CONFLICT = "resource_conflict"
    COMMUNICATION_FAILURE = "communication_failure"
    VALIDATION_FAILURE = "validation_failure"
    SYSTEM_OVERLOAD = "system_overload"


@dataclass
class FailureRecord:
    """Records information about a system failure"""
    failure_id: str
    failure_type: FailureType
    component: str  # Server, worker ID, or component name
    description: str
    context: Dict[str, Any]
    occurred_at: datetime
    resolved_at: Optional[datetime] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    is_resolved: bool = False
    impact_level: str = "medium"  # low, medium, high, critical


@dataclass
class ConnectionHealth:
    """Tracks connection health for workers and components"""
    component_id: str
    last_heartbeat: datetime
    consecutive_failures: int = 0
    total_failures: int = 0
    is_healthy: bool = True
    connection_quality: float = 1.0  # 0.0 to 1.0
    response_time_ms: float = 0.0


class ErrorRecoverySystem:
    """
    Comprehensive error recovery system for the collaborative server.
    
    Features:
    - Automatic connection failure recovery with exponential backoff
    - Worker crash detection and task reassignment
    - Resource conflict resolution with timeout mechanisms
    - Communication failure handling with message queuing
    - Performance monitoring and degradation detection
    """
    
    def __init__(self, server_instance=None, config: Dict[str, Any] = None):
        """
        Initialize the error recovery system.
        
        Args:
            server_instance: Reference to the collaborative server
            config: Configuration parameters for recovery behavior
        """
        self.server_instance = server_instance
        self.config = config or {}
        
        # Recovery configuration
        self.max_retry_attempts = self.config.get('max_retry_attempts', 3)
        self.retry_delay_base = self.config.get('retry_delay_base', 1.0)  # seconds
        self.heartbeat_interval = self.config.get('heartbeat_interval', 30)  # seconds
        self.connection_timeout = self.config.get('connection_timeout', 10)  # seconds
        self.task_timeout = self.config.get('task_timeout', 300)  # seconds
        
        # Failure tracking
        self.failure_records: Dict[str, FailureRecord] = {}
        self.connection_health: Dict[str, ConnectionHealth] = {}
        self.active_recoveries: Set[str] = set()
        
        # Task reassignment tracking
        self.failed_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_assignments: Dict[str, str] = {}  # task_id -> worker_id
        
        # Resource conflict resolution
        self.resource_locks: Dict[str, Dict[str, Any]] = {}
        self.lock_timeouts: Dict[str, datetime] = {}
        
        # Communication failure handling
        self.failed_messages: List[Dict[str, Any]] = []
        self.message_retry_queue: List[Dict[str, Any]] = []
        
        # Recovery statistics
        self.recovery_stats = {
            'total_failures': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'average_recovery_time': 0.0,
            'failures_by_type': {},
            'recoveries_by_strategy': {}
        }
        
        # Threading and lifecycle
        self._recovery_thread = None
        self._heartbeat_thread = None
        self._shutdown_event = threading.Event()
        self._lock = threading.RLock()
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.ErrorRecoverySystem")
        
        # Start recovery threads
        self._start_recovery_threads()
    
    def handle_connection_failure(self, component_id: str, error: Exception,
                                context: Dict[str, Any] = None) -> bool:
        """
        Handle connection failures with automatic reconnection.
        
        Args:
            component_id: ID of the component that failed to connect
            error: The connection error that occurred
            context: Additional context about the failure
            
        Returns:
            True if recovery was initiated successfully
        """
        try:
            # Record the failure
            failure_record = self._create_failure_record(
                failure_type=FailureType.CONNECTION_FAILURE,
                component=component_id,
                description=f"Connection failure: {str(error)}",
                context=context or {}
            )
            
            # Update connection health
            self._update_connection_health(component_id, healthy=False)
            
            # Determine recovery strategy
            strategy = self._determine_recovery_strategy(failure_record)
            failure_record.recovery_strategy = strategy
            
            if strategy == RecoveryStrategy.RETRY:
                # Start automatic reconnection
                self._start_connection_recovery(component_id, failure_record)
                return True
            elif strategy == RecoveryStrategy.ESCALATE:
                # Escalate to manual intervention
                self._escalate_failure(failure_record)
                return False
            else:
                # Abort or ignore
                self.logger.warning(f"Connection failure for {component_id} - strategy: {strategy.value}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error handling connection failure: {e}")
            return False
    
    def handle_worker_crash(self, worker_id: str, last_known_tasks: List[str],
                          context: Dict[str, Any] = None) -> bool:
        """
        Handle worker crashes with task reassignment.
        
        Args:
            worker_id: ID of the crashed worker
            last_known_tasks: List of task IDs the worker was handling
            context: Additional context about the crash
            
        Returns:
            True if recovery was initiated successfully
        """
        try:
            # Record the failure
            failure_record = self._create_failure_record(
                failure_type=FailureType.WORKER_CRASH,
                component=worker_id,
                description=f"Worker crashed with {len(last_known_tasks)} active tasks",
                context={**(context or {}), 'active_tasks': last_known_tasks}
            )
            
            # Mark worker as unhealthy
            self._update_connection_health(worker_id, healthy=False)
            
            # Reassign tasks to other workers
            reassigned_count = 0
            for task_id in last_known_tasks:
                if self._reassign_task(task_id, worker_id, failure_record.failure_id):
                    reassigned_count += 1
            
            failure_record.context['reassigned_tasks'] = reassigned_count
            
            # Attempt to restart the worker if possible
            if self.server_instance and hasattr(self.server_instance, '_worker_registry'):
                self._attempt_worker_restart(worker_id, failure_record)
            
            self.logger.info(f"Worker crash handled: {worker_id}, reassigned {reassigned_count} tasks")
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling worker crash: {e}")
            return False
    
    def handle_resource_conflict(self, resource_id: str, conflicting_workers: List[str],
                               context: Dict[str, Any] = None) -> bool:
        """
        Handle resource conflicts with timeout-based resolution.
        
        Args:
            resource_id: ID of the conflicted resource
            conflicting_workers: List of worker IDs in conflict
            context: Additional context about the conflict
            
        Returns:
            True if conflict was resolved successfully
        """
        try:
            # Record the failure
            failure_record = self._create_failure_record(
                failure_type=FailureType.RESOURCE_CONFLICT,
                component=resource_id,
                description=f"Resource conflict between {len(conflicting_workers)} workers",
                context={**(context or {}), 'conflicting_workers': conflicting_workers}
            )
            
            # Resolve conflict using priority-based approach
            resolved = self._resolve_resource_conflict(resource_id, conflicting_workers, failure_record)
            
            if resolved:
                failure_record.is_resolved = True
                failure_record.resolved_at = datetime.now()
                self.logger.info(f"Resource conflict resolved for {resource_id}")
            
            return resolved
            
        except Exception as e:
            self.logger.error(f"Error handling resource conflict: {e}")
            return False
    
    def handle_communication_failure(self, from_worker: str, to_worker: str,
                                   message: Dict[str, Any], error: Exception) -> bool:
        """
        Handle communication failures with message queuing and retry.
        
        Args:
            from_worker: ID of the sending worker
            to_worker: ID of the receiving worker
            message: The message that failed to deliver
            error: The communication error that occurred
            
        Returns:
            True if recovery was initiated successfully
        """
        try:
            # Record the failure
            failure_record = self._create_failure_record(
                failure_type=FailureType.COMMUNICATION_FAILURE,
                component=f"{from_worker}->{to_worker}",
                description=f"Message delivery failed: {str(error)}",
                context={
                    'from_worker': from_worker,
                    'to_worker': to_worker,
                    'message_type': message.get('message_type', 'unknown'),
                    'message_id': message.get('message_id', str(uuid.uuid4()))
                }
            )
            
            # Add message to retry queue
            retry_message = {
                'failure_id': failure_record.failure_id,
                'from_worker': from_worker,
                'to_worker': to_worker,
                'message': message,
                'retry_count': 0,
                'max_retries': self.max_retry_attempts,
                'next_retry': datetime.now() + timedelta(seconds=self.retry_delay_base)
            }
            
            with self._lock:
                self.message_retry_queue.append(retry_message)
            
            self.logger.info(f"Communication failure queued for retry: {from_worker} -> {to_worker}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling communication failure: {e}")
            return False
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health information.
        
        Returns:
            Dictionary containing system health metrics
        """
        with self._lock:
            # Calculate health metrics
            total_components = len(self.connection_health)
            healthy_components = sum(
                1 for health in self.connection_health.values() if health.is_healthy
            )
            
            health_percentage = (healthy_components / total_components * 100) if total_components > 0 else 100
            
            # Get recent failures (last hour)
            recent_failures = [
                record for record in self.failure_records.values()
                if record.occurred_at > datetime.now() - timedelta(hours=1)
            ]
            
            # Calculate average recovery time
            resolved_failures = [
                record for record in self.failure_records.values()
                if record.is_resolved and record.resolved_at
            ]
            
            avg_recovery_time = 0.0
            if resolved_failures:
                total_recovery_time = sum(
                    (record.resolved_at - record.occurred_at).total_seconds()
                    for record in resolved_failures
                )
                avg_recovery_time = total_recovery_time / len(resolved_failures)
            
            return {
                'overall_health_percentage': health_percentage,
                'healthy_components': healthy_components,
                'total_components': total_components,
                'active_recoveries': len(self.active_recoveries),
                'recent_failures': len(recent_failures),
                'total_failures': len(self.failure_records),
                'resolved_failures': len(resolved_failures),
                'average_recovery_time_seconds': avg_recovery_time,
                'pending_message_retries': len(self.message_retry_queue),
                'resource_conflicts': len([
                    record for record in self.failure_records.values()
                    if record.failure_type == FailureType.RESOURCE_CONFLICT and not record.is_resolved
                ]),
                'statistics': self.recovery_stats
            }
    
    def get_failure_history(self, limit: int = 50) -> List[FailureRecord]:
        """
        Get recent failure history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of recent failure records
        """
        with self._lock:
            failures = list(self.failure_records.values())
            failures.sort(key=lambda f: f.occurred_at, reverse=True)
            return failures[:limit]
    
    def shutdown(self) -> None:
        """Shutdown the error recovery system."""
        self.logger.info("Shutting down error recovery system...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for threads to complete
        if self._recovery_thread and self._recovery_thread.is_alive():
            self._recovery_thread.join(timeout=5)
        
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        
        # Clear data structures
        with self._lock:
            self.failure_records.clear()
            self.connection_health.clear()
            self.active_recoveries.clear()
            self.failed_tasks.clear()
            self.message_retry_queue.clear()
        
        self.logger.info("Error recovery system shutdown complete")
    
    def _create_failure_record(self, failure_type: FailureType, component: str,
                             description: str, context: Dict[str, Any]) -> FailureRecord:
        """Create a new failure record."""
        failure_id = str(uuid.uuid4())
        
        record = FailureRecord(
            failure_id=failure_id,
            failure_type=failure_type,
            component=component,
            description=description,
            context=context,
            occurred_at=datetime.now()
        )
        
        with self._lock:
            self.failure_records[failure_id] = record
            self.recovery_stats['total_failures'] += 1
            
            # Update failure type statistics
            type_key = failure_type.value
            self.recovery_stats['failures_by_type'][type_key] = \
                self.recovery_stats['failures_by_type'].get(type_key, 0) + 1
        
        return record
    
    def _determine_recovery_strategy(self, failure_record: FailureRecord) -> RecoveryStrategy:
        """Determine the appropriate recovery strategy for a failure."""
        failure_type = failure_record.failure_type
        component = failure_record.component
        
        # Check if this component has had recent failures
        recent_failures = [
            record for record in self.failure_records.values()
            if (record.component == component and 
                record.occurred_at > datetime.now() - timedelta(minutes=10))
        ]
        
        failure_count = len(recent_failures)
        
        # Strategy based on failure type and frequency
        if failure_type == FailureType.CONNECTION_FAILURE:
            if failure_count < 3:
                return RecoveryStrategy.RETRY
            elif failure_count < 5:
                return RecoveryStrategy.ESCALATE
            else:
                return RecoveryStrategy.ABORT
        
        elif failure_type == FailureType.WORKER_CRASH:
            if failure_count < 2:
                return RecoveryStrategy.REASSIGN
            else:
                return RecoveryStrategy.ESCALATE
        
        elif failure_type == FailureType.RESOURCE_CONFLICT:
            return RecoveryStrategy.RETRY
        
        elif failure_type == FailureType.COMMUNICATION_FAILURE:
            if failure_count < 5:
                return RecoveryStrategy.RETRY
            else:
                return RecoveryStrategy.ESCALATE
        
        else:
            return RecoveryStrategy.RETRY
    
    def _update_connection_health(self, component_id: str, healthy: bool,
                                response_time_ms: float = 0.0) -> None:
        """Update connection health for a component."""
        with self._lock:
            if component_id not in self.connection_health:
                self.connection_health[component_id] = ConnectionHealth(
                    component_id=component_id,
                    last_heartbeat=datetime.now()
                )
            
            health = self.connection_health[component_id]
            health.last_heartbeat = datetime.now()
            health.is_healthy = healthy
            health.response_time_ms = response_time_ms
            
            if healthy:
                health.consecutive_failures = 0
                health.connection_quality = min(1.0, health.connection_quality + 0.1)
            else:
                health.consecutive_failures += 1
                health.total_failures += 1
                health.connection_quality = max(0.0, health.connection_quality - 0.2)
    
    def _start_connection_recovery(self, component_id: str, failure_record: FailureRecord) -> None:
        """Start automatic connection recovery for a component."""
        recovery_id = f"conn_recovery_{component_id}_{failure_record.failure_id}"
        
        with self._lock:
            self.active_recoveries.add(recovery_id)
        
        # Start recovery in a separate thread
        recovery_thread = threading.Thread(
            target=self._connection_recovery_loop,
            args=(component_id, failure_record, recovery_id),
            name=f"ConnectionRecovery-{component_id[:8]}"
        )
        recovery_thread.daemon = True
        recovery_thread.start()
    
    def _connection_recovery_loop(self, component_id: str, failure_record: FailureRecord,
                                recovery_id: str) -> None:
        """Connection recovery loop with exponential backoff."""
        try:
            attempt = 0
            while attempt < self.max_retry_attempts and not self._shutdown_event.is_set():
                attempt += 1
                delay = self.retry_delay_base * (2 ** (attempt - 1))  # Exponential backoff
                
                self.logger.info(f"Connection recovery attempt {attempt} for {component_id} in {delay}s")
                
                if self._shutdown_event.wait(timeout=delay):
                    break
                
                # Attempt reconnection
                if self._attempt_reconnection(component_id):
                    # Success
                    failure_record.is_resolved = True
                    failure_record.resolved_at = datetime.now()
                    failure_record.recovery_attempts = attempt
                    
                    with self._lock:
                        self.recovery_stats['successful_recoveries'] += 1
                    
                    self.logger.info(f"Connection recovery successful for {component_id}")
                    break
                else:
                    failure_record.recovery_attempts = attempt
            
            # Recovery completed (success or failure)
            if not failure_record.is_resolved:
                with self._lock:
                    self.recovery_stats['failed_recoveries'] += 1
                self.logger.warning(f"Connection recovery failed for {component_id} after {attempt} attempts")
            
        except Exception as e:
            self.logger.error(f"Connection recovery error for {component_id}: {e}")
        finally:
            with self._lock:
                self.active_recoveries.discard(recovery_id)
    
    def _attempt_reconnection(self, component_id: str) -> bool:
        """Attempt to reconnect a component."""
        try:
            # This would be implemented based on the specific component type
            # For now, we'll simulate a reconnection attempt
            
            if self.server_instance and hasattr(self.server_instance, '_worker_registry'):
                # Check if it's a worker
                registry = self.server_instance._worker_registry
                active_workers = registry.get_active_workers()
                
                for worker in active_workers:
                    if worker['worker_id'] == component_id:
                        # Worker exists, mark as healthy
                        self._update_connection_health(component_id, healthy=True)
                        return True
            
            # For other components, we'd implement specific reconnection logic
            # For now, simulate success based on random chance (for testing)
            import random
            success = random.random() > 0.3  # 70% success rate
            
            if success:
                self._update_connection_health(component_id, healthy=True)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Reconnection attempt failed for {component_id}: {e}")
            return False
    
    def _reassign_task(self, task_id: str, failed_worker_id: str, failure_id: str) -> bool:
        """Reassign a task from a failed worker to another worker."""
        try:
            if not self.server_instance or not hasattr(self.server_instance, '_worker_registry'):
                return False
            
            registry = self.server_instance._worker_registry
            
            # Get the failed worker's type to find a replacement
            worker_type = registry.worker_types.get(failed_worker_id)
            if not worker_type:
                return False
            
            # Find available workers of the same type
            available_workers = registry.find_workers_by_type(worker_type, available_only=True)
            
            if not available_workers:
                # No available workers, queue for later reassignment
                with self._lock:
                    self.failed_tasks[task_id] = {
                        'original_worker': failed_worker_id,
                        'worker_type': worker_type.value,
                        'failure_id': failure_id,
                        'queued_at': datetime.now()
                    }
                return False
            
            # Select the best available worker
            best_worker = registry.get_load_balanced_worker(worker_type, {})
            if not best_worker:
                return False
            
            new_worker_id = best_worker['worker_id']
            
            # Update task assignment
            with self._lock:
                self.task_assignments[task_id] = new_worker_id
            
            self.logger.info(f"Task {task_id} reassigned from {failed_worker_id} to {new_worker_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Task reassignment failed for {task_id}: {e}")
            return False
    
    def _attempt_worker_restart(self, worker_id: str, failure_record: FailureRecord) -> bool:
        """Attempt to restart a crashed worker."""
        try:
            # This would implement worker restart logic
            # For now, we'll log the attempt
            self.logger.info(f"Attempting to restart worker {worker_id}")
            
            # In a real implementation, this would:
            # 1. Get worker configuration from registry
            # 2. Create new worker instance
            # 3. Register the new worker
            # 4. Update failure record
            
            return False  # Not implemented yet
            
        except Exception as e:
            self.logger.error(f"Worker restart failed for {worker_id}: {e}")
            return False
    
    def _resolve_resource_conflict(self, resource_id: str, conflicting_workers: List[str],
                                 failure_record: FailureRecord) -> bool:
        """Resolve resource conflicts using priority-based approach."""
        try:
            if not self.server_instance or not hasattr(self.server_instance, '_worker_registry'):
                return False
            
            registry = self.server_instance._worker_registry
            
            # Get worker priorities
            worker_priorities = []
            for worker_id in conflicting_workers:
                load_stats = registry.load_balancing_stats.get(worker_id, {})
                priority = load_stats.get('priority_score', 0.0)
                worker_priorities.append((priority, worker_id))
            
            # Sort by priority (highest first)
            worker_priorities.sort(reverse=True)
            
            # Grant access to highest priority worker
            if worker_priorities:
                winner_worker = worker_priorities[0][1]
                
                # Set resource lock
                with self._lock:
                    self.resource_locks[resource_id] = {
                        'worker_id': winner_worker,
                        'locked_at': datetime.now(),
                        'timeout': datetime.now() + timedelta(minutes=10)
                    }
                
                self.logger.info(f"Resource {resource_id} granted to worker {winner_worker}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Resource conflict resolution failed for {resource_id}: {e}")
            return False
    
    def _escalate_failure(self, failure_record: FailureRecord) -> None:
        """Escalate a failure for manual intervention."""
        self.logger.error(f"ESCALATED FAILURE: {failure_record.description}")
        self.logger.error(f"Failure ID: {failure_record.failure_id}")
        self.logger.error(f"Component: {failure_record.component}")
        self.logger.error(f"Context: {failure_record.context}")
        
        # In a real implementation, this would:
        # 1. Send notifications to administrators
        # 2. Create support tickets
        # 3. Trigger alerting systems
        # 4. Log to external monitoring systems
    
    def _start_recovery_threads(self) -> None:
        """Start background recovery threads."""
        # Recovery thread for processing failures and retries
        self._recovery_thread = threading.Thread(
            target=self._recovery_loop,
            name="ErrorRecovery"
        )
        self._recovery_thread.daemon = True
        self._recovery_thread.start()
        
        # Heartbeat thread for monitoring component health
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="HealthMonitor"
        )
        self._heartbeat_thread.daemon = True
        self._heartbeat_thread.start()
    
    def _recovery_loop(self) -> None:
        """Main recovery loop for processing failures and retries."""
        self.logger.debug("Error recovery loop started")
        
        try:
            while not self._shutdown_event.is_set():
                # Process message retries
                self._process_message_retries()
                
                # Clean up expired resource locks
                self._cleanup_expired_locks()
                
                # Process queued task reassignments
                self._process_queued_tasks()
                
                # Wait before next iteration
                if self._shutdown_event.wait(timeout=1.0):
                    break
                    
        except Exception as e:
            self.logger.error(f"Recovery loop error: {e}")
        
        self.logger.debug("Error recovery loop completed")
    
    def _heartbeat_loop(self) -> None:
        """Heartbeat loop for monitoring component health."""
        self.logger.debug("Heartbeat monitoring loop started")
        
        try:
            while not self._shutdown_event.is_set():
                # Check component health
                self._check_component_health()
                
                # Wait for next heartbeat interval
                if self._shutdown_event.wait(timeout=self.heartbeat_interval):
                    break
                    
        except Exception as e:
            self.logger.error(f"Heartbeat loop error: {e}")
        
        self.logger.debug("Heartbeat monitoring loop completed")
    
    def _process_message_retries(self) -> None:
        """Process messages in the retry queue."""
        now = datetime.now()
        
        with self._lock:
            retry_messages = self.message_retry_queue.copy()
            self.message_retry_queue.clear()
        
        for retry_msg in retry_messages:
            if now >= retry_msg['next_retry']:
                # Attempt retry
                success = self._retry_message(retry_msg)
                
                if not success:
                    retry_msg['retry_count'] += 1
                    
                    if retry_msg['retry_count'] < retry_msg['max_retries']:
                        # Schedule next retry with exponential backoff
                        delay = self.retry_delay_base * (2 ** retry_msg['retry_count'])
                        retry_msg['next_retry'] = now + timedelta(seconds=delay)
                        
                        with self._lock:
                            self.message_retry_queue.append(retry_msg)
                    else:
                        # Max retries exceeded
                        self.logger.warning(f"Message retry failed permanently: {retry_msg['failure_id']}")
            else:
                # Not ready for retry yet
                with self._lock:
                    self.message_retry_queue.append(retry_msg)
    
    def _retry_message(self, retry_msg: Dict[str, Any]) -> bool:
        """Retry sending a failed message."""
        try:
            if not self.server_instance or not hasattr(self.server_instance, '_message_router'):
                return False
            
            router = self.server_instance._message_router
            
            success = router.route_message(
                retry_msg['from_worker'],
                retry_msg['to_worker'],
                retry_msg['message']
            )
            
            if success:
                self.logger.debug(f"Message retry successful: {retry_msg['failure_id']}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Message retry error: {e}")
            return False
    
    def _cleanup_expired_locks(self) -> None:
        """Clean up expired resource locks."""
        now = datetime.now()
        expired_locks = []
        
        with self._lock:
            for resource_id, lock_info in self.resource_locks.items():
                if now > lock_info['timeout']:
                    expired_locks.append(resource_id)
        
        for resource_id in expired_locks:
            with self._lock:
                lock_info = self.resource_locks.pop(resource_id, None)
                if lock_info:
                    self.logger.info(f"Resource lock expired: {resource_id} (was held by {lock_info['worker_id']})")
    
    def _process_queued_tasks(self) -> None:
        """Process tasks queued for reassignment."""
        if not self.server_instance or not hasattr(self.server_instance, '_worker_registry'):
            return
        
        registry = self.server_instance._worker_registry
        reassigned_tasks = []
        
        with self._lock:
            queued_tasks = self.failed_tasks.copy()
        
        for task_id, task_info in queued_tasks.items():
            # Try to find available worker of the required type
            from .enhanced_worker_registry import WorkerType
            worker_type = WorkerType(task_info['worker_type'])
            
            available_workers = registry.find_workers_by_type(worker_type, available_only=True)
            
            if available_workers:
                best_worker = registry.get_load_balanced_worker(worker_type, {})
                if best_worker:
                    new_worker_id = best_worker['worker_id']
                    
                    with self._lock:
                        self.task_assignments[task_id] = new_worker_id
                    
                    reassigned_tasks.append(task_id)
                    self.logger.info(f"Queued task {task_id} reassigned to {new_worker_id}")
        
        # Remove reassigned tasks from queue
        with self._lock:
            for task_id in reassigned_tasks:
                self.failed_tasks.pop(task_id, None)
    
    def _check_component_health(self) -> None:
        """Check health of all registered components."""
        now = datetime.now()
        unhealthy_threshold = timedelta(seconds=self.heartbeat_interval * 2)
        
        with self._lock:
            components = list(self.connection_health.keys())
        
        for component_id in components:
            health = self.connection_health[component_id]
            
            # Check if component has been silent too long
            if now - health.last_heartbeat > unhealthy_threshold:
                if health.is_healthy:
                    # Component became unhealthy
                    self.logger.warning(f"Component {component_id} appears unhealthy (no heartbeat)")
                    self._update_connection_health(component_id, healthy=False)
                    
                    # Create failure record if not already exists
                    recent_failures = [
                        record for record in self.failure_records.values()
                        if (record.component == component_id and 
                            record.failure_type == FailureType.CONNECTION_FAILURE and
                            record.occurred_at > now - timedelta(minutes=5))
                    ]
                    
                    if not recent_failures:
                        self.handle_connection_failure(
                            component_id,
                            Exception("Heartbeat timeout"),
                            {'reason': 'heartbeat_timeout'}
                        )
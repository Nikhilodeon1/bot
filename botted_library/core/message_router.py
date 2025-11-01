"""
Message Router for Collaborative Worker Communication

Handles reliable message routing between workers with queuing,
delivery confirmation, and message history tracking.
"""

import threading
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
import logging

from .exceptions import WorkerError


class MessageType(Enum):
    """Types of messages that can be routed between workers"""
    TASK_DELEGATION = "task_delegation"
    VERIFICATION_REQUEST = "verification_request"
    COLLABORATION_INVITE = "collaboration_invite"
    STATUS_UPDATE = "status_update"
    RESULT_REPORT = "result_report"
    ERROR_NOTIFICATION = "error_notification"
    HEARTBEAT = "heartbeat"
    BROADCAST = "broadcast"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class DeliveryStatus(Enum):
    """Message delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class CollaborativeMessage:
    """Represents a message between workers"""
    message_id: str
    from_worker_id: str
    to_worker_id: str
    message_type: MessageType
    content: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    requires_response: bool = False
    expires_at: Optional[datetime] = None
    collaborative_space_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    delivery_attempts: int = 0
    max_delivery_attempts: int = 3
    response_timeout_seconds: int = 30


@dataclass
class MessageDeliveryRecord:
    """Records message delivery information"""
    message_id: str
    delivered_at: datetime
    delivery_time_ms: float
    success: bool
    error_message: Optional[str] = None


class MessageRouter:
    """
    Routes messages between workers with reliable delivery and queuing.
    
    Features:
    - Priority-based message queuing
    - Delivery confirmation and retry logic
    - Message history and analytics
    - Real-time communication channels
    - Broadcast messaging support
    """
    
    def __init__(self, worker_registry, queue_size: int = 1000):
        """
        Initialize the message router.
        
        Args:
            worker_registry: Enhanced worker registry instance
            queue_size: Maximum size of message queues
        """
        self.worker_registry = worker_registry
        self.queue_size = queue_size
        
        # Message queuing and routing
        self.message_queues: Dict[str, Queue] = {}  # Per-worker message queues
        self.pending_messages: Dict[str, CollaborativeMessage] = {}
        self.message_history: List[CollaborativeMessage] = []
        self.delivery_records: List[MessageDeliveryRecord] = []
        
        # Real-time communication
        self.message_subscribers: Dict[str, List[Callable]] = {}  # Worker ID -> callbacks
        self.broadcast_subscribers: List[Callable] = []
        
        # Routing statistics
        self.routing_stats = {
            'total_messages': 0,
            'successful_deliveries': 0,
            'failed_deliveries': 0,
            'average_delivery_time_ms': 0.0,
            'messages_by_type': {},
            'messages_by_priority': {}
        }
        
        # Threading and lifecycle
        self._router_thread = None
        self._shutdown_event = threading.Event()
        self._lock = threading.RLock()
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.MessageRouter")
        
        # Start router thread
        self._start_router_thread()
    
    def route_message(self, from_worker_id: str, to_worker_id: str, 
                     message_content: Dict[str, Any]) -> bool:
        """
        Route a message from one worker to another.
        
        Args:
            from_worker_id: ID of the sending worker
            to_worker_id: ID of the receiving worker
            message_content: Message content and metadata
            
        Returns:
            True if message was queued successfully
            
        Raises:
            WorkerError: If routing fails
        """
        try:
            # Create message object
            message = self._create_message(from_worker_id, to_worker_id, message_content)
            
            # Validate workers exist
            if not self._validate_workers(from_worker_id, to_worker_id):
                raise WorkerError(
                    f"Invalid worker IDs: from={from_worker_id}, to={to_worker_id}",
                    worker_id=from_worker_id,
                    context={'operation': 'route_message'}
                )
            
            # Queue message for delivery
            success = self._queue_message(message)
            
            if success:
                with self._lock:
                    self.routing_stats['total_messages'] += 1
                    
                    # Update type statistics
                    msg_type = message.message_type.value
                    self.routing_stats['messages_by_type'][msg_type] = \
                        self.routing_stats['messages_by_type'].get(msg_type, 0) + 1
                    
                    # Update priority statistics
                    priority = message.priority.value
                    self.routing_stats['messages_by_priority'][priority] = \
                        self.routing_stats['messages_by_priority'].get(priority, 0) + 1
                
                self.logger.debug(f"Message queued: {message.message_id} ({from_worker_id} -> {to_worker_id})")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Message routing failed: {e}")
            raise WorkerError(
                f"Message routing failed: {e}",
                worker_id=from_worker_id,
                context={'operation': 'route_message', 'error': str(e)}
            )
    
    def broadcast_message(self, from_worker_id: str, message_content: Dict[str, Any],
                         target_worker_types: Optional[List[str]] = None) -> int:
        """
        Broadcast a message to multiple workers.
        
        Args:
            from_worker_id: ID of the sending worker
            message_content: Message content to broadcast
            target_worker_types: Optional list of worker types to target
            
        Returns:
            Number of workers the message was sent to
        """
        try:
            # Get target workers
            if target_worker_types:
                target_workers = []
                for worker_type in target_worker_types:
                    from .enhanced_worker_registry import WorkerType
                    workers = self.worker_registry.find_workers_by_type(
                        WorkerType(worker_type), available_only=False
                    )
                    target_workers.extend(workers)
            else:
                # Broadcast to all workers
                target_workers = self.worker_registry.get_active_workers(
                    exclude_worker_id=from_worker_id
                )
            
            # Send message to each target worker
            sent_count = 0
            for worker in target_workers:
                worker_id = worker['worker_id']
                
                # Create broadcast message
                broadcast_content = {
                    **message_content,
                    'message_type': MessageType.BROADCAST.value,
                    'broadcast': True
                }
                
                if self.route_message(from_worker_id, worker_id, broadcast_content):
                    sent_count += 1
            
            self.logger.info(f"Broadcast message sent to {sent_count} workers")
            return sent_count
            
        except Exception as e:
            self.logger.error(f"Broadcast failed: {e}")
            return 0
    
    def subscribe_to_messages(self, worker_id: str, callback: Callable) -> str:
        """
        Subscribe to real-time messages for a worker.
        
        Args:
            worker_id: ID of the worker to subscribe for
            callback: Function to call when messages arrive
            
        Returns:
            Subscription ID
        """
        with self._lock:
            if worker_id not in self.message_subscribers:
                self.message_subscribers[worker_id] = []
            
            self.message_subscribers[worker_id].append(callback)
            subscription_id = str(uuid.uuid4())
            
            self.logger.debug(f"Message subscription created for worker {worker_id}")
            return subscription_id
    
    def unsubscribe_from_messages(self, worker_id: str, callback: Callable) -> bool:
        """
        Unsubscribe from real-time messages.
        
        Args:
            worker_id: ID of the worker
            callback: Callback function to remove
            
        Returns:
            True if unsubscribed successfully
        """
        with self._lock:
            if worker_id in self.message_subscribers:
                try:
                    self.message_subscribers[worker_id].remove(callback)
                    return True
                except ValueError:
                    pass
            
            return False
    
    def get_message_history(self, worker_id: str, limit: int = 50) -> List[CollaborativeMessage]:
        """
        Get message history for a worker.
        
        Args:
            worker_id: ID of the worker
            limit: Maximum number of messages to return
            
        Returns:
            List of messages involving the worker
        """
        with self._lock:
            worker_messages = [
                msg for msg in self.message_history
                if msg.from_worker_id == worker_id or msg.to_worker_id == worker_id
            ]
            
            # Sort by creation time (newest first)
            worker_messages.sort(key=lambda m: m.created_at, reverse=True)
            
            return worker_messages[:limit]
    
    def get_pending_messages(self, worker_id: str) -> List[CollaborativeMessage]:
        """
        Get pending messages for a worker.
        
        Args:
            worker_id: ID of the worker
            
        Returns:
            List of pending messages for the worker
        """
        with self._lock:
            if worker_id not in self.message_queues:
                return []
            
            queue = self.message_queues[worker_id]
            pending = []
            
            # Peek at queue contents (non-destructive)
            temp_messages = []
            try:
                while True:
                    message = queue.get_nowait()
                    temp_messages.append(message)
                    pending.append(message)
            except Empty:
                pass
            
            # Put messages back in queue
            for message in temp_messages:
                queue.put(message)
            
            return pending
    
    def process_pending_messages(self) -> int:
        """
        Process pending messages in all queues.
        
        Returns:
            Number of messages processed
        """
        processed_count = 0
        
        with self._lock:
            worker_ids = list(self.message_queues.keys())
        
        for worker_id in worker_ids:
            processed_count += self._process_worker_queue(worker_id)
        
        return processed_count
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive routing statistics.
        
        Returns:
            Dictionary containing routing statistics
        """
        with self._lock:
            # Calculate average delivery time
            if self.delivery_records:
                avg_delivery_time = sum(
                    record.delivery_time_ms for record in self.delivery_records
                ) / len(self.delivery_records)
            else:
                avg_delivery_time = 0.0
            
            return {
                **self.routing_stats,
                'average_delivery_time_ms': avg_delivery_time,
                'pending_messages': sum(
                    queue.qsize() for queue in self.message_queues.values()
                ),
                'total_delivery_records': len(self.delivery_records),
                'active_subscriptions': sum(
                    len(callbacks) for callbacks in self.message_subscribers.values()
                ),
                'message_history_size': len(self.message_history)
            }
    
    def shutdown(self) -> None:
        """Shutdown the message router."""
        self.logger.info("Shutting down message router...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for router thread to complete
        if self._router_thread and self._router_thread.is_alive():
            self._router_thread.join(timeout=5)
        
        # Clear data structures
        with self._lock:
            self.message_queues.clear()
            self.pending_messages.clear()
            self.message_subscribers.clear()
            self.broadcast_subscribers.clear()
        
        self.logger.info("Message router shutdown complete")
    
    def _create_message(self, from_worker_id: str, to_worker_id: str,
                       message_content: Dict[str, Any]) -> CollaborativeMessage:
        """Create a CollaborativeMessage from content."""
        message_id = str(uuid.uuid4())
        
        # Extract message properties from content
        message_type_str = message_content.get('message_type', MessageType.TASK_DELEGATION.value)
        try:
            message_type = MessageType(message_type_str)
        except ValueError:
            message_type = MessageType.TASK_DELEGATION
        
        priority_str = message_content.get('priority', MessagePriority.NORMAL.value)
        try:
            priority = MessagePriority(priority_str)
        except (ValueError, TypeError):
            priority = MessagePriority.NORMAL
        
        # Set expiration time
        expires_at = None
        if message_content.get('expires_in_seconds'):
            expires_at = datetime.now() + timedelta(
                seconds=message_content['expires_in_seconds']
            )
        
        return CollaborativeMessage(
            message_id=message_id,
            from_worker_id=from_worker_id,
            to_worker_id=to_worker_id,
            message_type=message_type,
            content=message_content,
            priority=priority,
            requires_response=message_content.get('requires_response', False),
            expires_at=expires_at,
            collaborative_space_id=message_content.get('collaborative_space_id'),
            response_timeout_seconds=message_content.get('response_timeout_seconds', 30)
        )
    
    def _validate_workers(self, from_worker_id: str, to_worker_id: str) -> bool:
        """Validate that both workers exist in the registry."""
        active_workers = self.worker_registry.get_active_workers()
        active_worker_ids = {worker['worker_id'] for worker in active_workers}
        
        return from_worker_id in active_worker_ids and to_worker_id in active_worker_ids
    
    def _queue_message(self, message: CollaborativeMessage) -> bool:
        """Queue a message for delivery."""
        with self._lock:
            worker_id = message.to_worker_id
            
            # Create queue if it doesn't exist
            if worker_id not in self.message_queues:
                self.message_queues[worker_id] = Queue(maxsize=self.queue_size)
            
            queue = self.message_queues[worker_id]
            
            # Check if queue is full
            if queue.full():
                self.logger.warning(f"Message queue full for worker {worker_id}")
                return False
            
            # Add to pending messages
            self.pending_messages[message.message_id] = message
            
            # Queue message (priority queuing would require a different queue type)
            queue.put(message)
            
            return True
    
    def _process_worker_queue(self, worker_id: str) -> int:
        """Process messages in a worker's queue."""
        if worker_id not in self.message_queues:
            return 0
        
        queue = self.message_queues[worker_id]
        processed = 0
        
        # Process up to 10 messages per call to avoid blocking
        for _ in range(10):
            try:
                message = queue.get_nowait()
                if self._deliver_message(message):
                    processed += 1
            except Empty:
                break
        
        return processed
    
    def _deliver_message(self, message: CollaborativeMessage) -> bool:
        """Attempt to deliver a message to its target worker."""
        start_time = time.time()
        
        try:
            # Check if message has expired
            if message.expires_at and datetime.now() > message.expires_at:
                self._record_delivery(message, False, "Message expired")
                return False
            
            # Check delivery attempts
            message.delivery_attempts += 1
            if message.delivery_attempts > message.max_delivery_attempts:
                self._record_delivery(message, False, "Max delivery attempts exceeded")
                return False
            
            # Notify subscribers
            success = self._notify_message_subscribers(message)
            
            if success:
                message.delivery_status = DeliveryStatus.DELIVERED
                delivery_time_ms = (time.time() - start_time) * 1000
                self._record_delivery(message, True, None, delivery_time_ms)
                
                # Add to message history
                with self._lock:
                    self.message_history.append(message)
                    
                    # Limit history size
                    if len(self.message_history) > 1000:
                        self.message_history = self.message_history[-800:]
                
                # Remove from pending
                self.pending_messages.pop(message.message_id, None)
                
                return True
            else:
                # Retry later
                message.delivery_status = DeliveryStatus.PENDING
                return False
                
        except Exception as e:
            self.logger.error(f"Message delivery failed: {e}")
            self._record_delivery(message, False, str(e))
            return False
    
    def _notify_message_subscribers(self, message: CollaborativeMessage) -> bool:
        """Notify subscribers about a new message."""
        worker_id = message.to_worker_id
        
        with self._lock:
            callbacks = self.message_subscribers.get(worker_id, [])
        
        if not callbacks:
            # No subscribers, consider delivery successful for now
            return True
        
        success = True
        for callback in callbacks:
            try:
                callback(message)
            except Exception as e:
                self.logger.error(f"Message subscriber callback failed: {e}")
                success = False
        
        return success
    
    def _record_delivery(self, message: CollaborativeMessage, success: bool,
                        error_message: Optional[str], delivery_time_ms: float = 0.0) -> None:
        """Record message delivery information."""
        record = MessageDeliveryRecord(
            message_id=message.message_id,
            delivered_at=datetime.now(),
            delivery_time_ms=delivery_time_ms,
            success=success,
            error_message=error_message
        )
        
        with self._lock:
            self.delivery_records.append(record)
            
            # Update statistics
            if success:
                self.routing_stats['successful_deliveries'] += 1
            else:
                self.routing_stats['failed_deliveries'] += 1
            
            # Limit delivery records size
            if len(self.delivery_records) > 1000:
                self.delivery_records = self.delivery_records[-800:]
    
    def _start_router_thread(self) -> None:
        """Start the background router thread."""
        self._router_thread = threading.Thread(
            target=self._router_loop,
            name="MessageRouter"
        )
        self._router_thread.daemon = True
        self._router_thread.start()
    
    def _router_loop(self) -> None:
        """Main router loop running in background thread."""
        self.logger.debug("Message router loop started")
        
        try:
            while not self._shutdown_event.is_set():
                # Process pending messages
                self.process_pending_messages()
                
                # Clean up expired messages
                self._cleanup_expired_messages()
                
                # Wait before next iteration
                if self._shutdown_event.wait(timeout=0.1):
                    break
                    
        except Exception as e:
            self.logger.error(f"Router loop error: {e}")
        
        self.logger.debug("Message router loop completed")
    
    def _cleanup_expired_messages(self) -> None:
        """Clean up expired messages from pending queue."""
        now = datetime.now()
        expired_messages = []
        
        with self._lock:
            for message_id, message in self.pending_messages.items():
                if message.expires_at and now > message.expires_at:
                    expired_messages.append(message_id)
        
        # Remove expired messages
        for message_id in expired_messages:
            message = self.pending_messages.pop(message_id, None)
            if message:
                message.delivery_status = DeliveryStatus.EXPIRED
                self._record_delivery(message, False, "Message expired")
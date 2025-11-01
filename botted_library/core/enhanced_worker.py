"""
Enhanced Worker Base Class for Collaborative System

Provides the foundation for specialized worker types (Planner, Executor, Verifier)
with collaborative capabilities and server communication.
"""

import uuid
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .worker import Worker
from .enhanced_worker_registry import WorkerType
from .message_router import CollaborativeMessage, MessageType
from .exceptions import WorkerError


@dataclass
class ServerConnection:
    """Represents a connection to the collaborative server"""
    server_instance: Any
    worker_id: str
    connection_id: str
    connected_at: datetime
    is_active: bool = True


class EnhancedWorker(Worker):
    """
    Enhanced worker with collaborative capabilities.
    
    Extends the base Worker class with:
    - Server connection and communication
    - Inter-worker messaging and collaboration
    - Collaborative space participation
    - Specialized worker type behaviors
    """
    
    def __init__(self, name: str, role: str, worker_type: WorkerType,
                 memory_system, knowledge_validator, browser_controller, task_executor,
                 server_connection: Optional[ServerConnection] = None,
                 worker_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize enhanced worker with collaborative capabilities.
        
        Args:
            name: Human-readable name for the worker
            role: Worker's role/title
            worker_type: Specialized worker type (Planner, Executor, Verifier)
            memory_system: Memory system instance
            knowledge_validator: Knowledge validator instance
            browser_controller: Browser controller instance
            task_executor: Task executor instance
            server_connection: Connection to collaborative server
            worker_id: Optional unique identifier
            config: Optional configuration parameters
        """
        # Initialize base worker
        super().__init__(
            memory_system=memory_system,
            knowledge_validator=knowledge_validator,
            browser_controller=browser_controller,
            task_executor=task_executor,
            worker_id=worker_id,
            config=config
        )
        
        # Enhanced worker properties
        self.name = name
        self.role = role
        self.worker_type = worker_type
        self.server_connection = server_connection
        
        # Collaborative capabilities
        self.collaborative_spaces: Dict[str, Any] = {}
        self.active_collaborations: Dict[str, Dict[str, Any]] = {}
        self.message_handlers: Dict[MessageType, Callable] = {}
        
        # Communication state
        self._message_queue = []
        self._message_lock = threading.Lock()
        self._is_connected = False
        
        # Performance tracking
        self.collaboration_stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'tasks_delegated': 0,
            'tasks_received': 0,
            'collaborations_initiated': 0,
            'collaborations_joined': 0
        }
        
        # Setup default message handlers
        self._setup_default_message_handlers()
        
        # Connect to server if connection provided
        if server_connection:
            self.connect_to_server()
    
    def connect_to_server(self) -> bool:
        """
        Connect to the collaborative server.
        
        Returns:
            True if connection successful
            
        Raises:
            WorkerError: If connection fails
        """
        if not self.server_connection:
            raise WorkerError(
                "No server connection configured",
                worker_id=self.worker_id,
                context={'operation': 'connect_to_server'}
            )
        
        try:
            server = self.server_connection.server_instance
            
            # Register with server
            worker_info = {
                'name': self.name,
                'role': self.role,
                'worker_type': self.worker_type.value,
                'capabilities': self._get_enhanced_capabilities(),
                'enhanced_capabilities': self._get_detailed_capabilities(),
                'worker_instance': self,
                'max_concurrent_tasks': self.config.get('max_concurrent_tasks', 3)
            }
            
            registration_id = server.register_worker(self.worker_id, worker_info)
            
            # Setup message subscription
            message_router = server.get_worker_registry()._message_router if hasattr(server.get_worker_registry(), '_message_router') else None
            if message_router:
                message_router.subscribe_to_messages(self.worker_id, self._handle_incoming_message)
            
            self._is_connected = True
            self.server_connection.is_active = True
            
            self.logger.info(f"Enhanced worker {self.name} connected to server")
            return True
            
        except Exception as e:
            self.logger.error(f"Server connection failed: {e}")
            raise WorkerError(
                f"Server connection failed: {e}",
                worker_id=self.worker_id,
                context={'operation': 'connect_to_server', 'error': str(e)}
            )
    
    def disconnect_from_server(self) -> None:
        """Disconnect from the collaborative server."""
        if not self._is_connected or not self.server_connection:
            return
        
        try:
            server = self.server_connection.server_instance
            server.unregister_worker(self.worker_id)
            
            self._is_connected = False
            self.server_connection.is_active = False
            
            self.logger.info(f"Enhanced worker {self.name} disconnected from server")
            
        except Exception as e:
            self.logger.error(f"Server disconnection error: {e}")
    
    def send_message_to_worker(self, target_worker_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to another worker through the server.
        
        Args:
            target_worker_id: ID of the target worker
            message: Message content and metadata
            
        Returns:
            True if message was sent successfully
            
        Raises:
            WorkerError: If not connected to server or sending fails
        """
        if not self._is_connected:
            raise WorkerError(
                "Not connected to server",
                worker_id=self.worker_id,
                context={'operation': 'send_message_to_worker'}
            )
        
        try:
            server = self.server_connection.server_instance
            success = server.route_message(self.worker_id, target_worker_id, message)
            
            if success:
                self.collaboration_stats['messages_sent'] += 1
                self.logger.debug(f"Message sent to {target_worker_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send message to {target_worker_id}: {e}")
            raise WorkerError(
                f"Message sending failed: {e}",
                worker_id=self.worker_id,
                context={'operation': 'send_message_to_worker', 'error': str(e)}
            )
    
    def join_collaborative_space(self, space_id: str) -> bool:
        """
        Join a collaborative space.
        
        Args:
            space_id: ID of the collaborative space to join
            
        Returns:
            True if joined successfully
        """
        if not self._is_connected:
            self.logger.warning("Cannot join collaborative space - not connected to server")
            return False
        
        try:
            server = self.server_connection.server_instance
            space = server.get_collaborative_space(space_id)
            
            if not space:
                self.logger.error(f"Collaborative space {space_id} not found")
                return False
            
            # Add this worker as a participant
            success = space.add_participant(
                worker_id=self.worker_id,
                worker_name=self.name,
                worker_type=self.worker_type.value
            )
            
            if success:
                # Subscribe to space messages
                space.subscribe_to_messages(self.worker_id, self._handle_space_message)
                
                # Track the space locally
                self.collaborative_spaces[space_id] = {
                    'joined_at': datetime.now(),
                    'active': True,
                    'space_instance': space
                }
                
                self.collaboration_stats['collaborations_joined'] += 1
                self.logger.info(f"Joined collaborative space: {space_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to join collaborative space {space_id}: {e}")
            return False
    
    def leave_collaborative_space(self, space_id: str) -> bool:
        """
        Leave a collaborative space.
        
        Args:
            space_id: ID of the collaborative space to leave
            
        Returns:
            True if left successfully
        """
        if space_id not in self.collaborative_spaces:
            self.logger.warning(f"Not in collaborative space {space_id}")
            return False
        
        try:
            space_info = self.collaborative_spaces[space_id]
            space = space_info.get('space_instance')
            
            if space:
                # Remove from space participants
                space.remove_participant(self.worker_id)
                
                # Unsubscribe from space messages
                space.unsubscribe_from_messages(self.worker_id)
            
            # Update local tracking
            space_info['active'] = False
            
            self.logger.info(f"Left collaborative space: {space_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to leave collaborative space {space_id}: {e}")
            return False
    
    def access_shared_whiteboard(self, space_id: str):
        """
        Access the shared whiteboard in a collaborative space.
        
        Args:
            space_id: ID of the collaborative space
            
        Returns:
            SharedWhiteboard instance or None if not available
        """
        if space_id not in self.collaborative_spaces:
            self.logger.warning(f"Not in collaborative space {space_id}")
            return None
        
        space_info = self.collaborative_spaces[space_id]
        space = space_info.get('space_instance')
        
        if space:
            whiteboard = space.get_shared_whiteboard()
            
            # If no whiteboard exists, create one
            if not whiteboard:
                whiteboard = space.create_shared_whiteboard()
                self.logger.info(f"Created shared whiteboard for space {space_id}")
            
            # Subscribe to whiteboard changes
            if whiteboard:
                whiteboard.subscribe_to_changes(self.worker_id, self._handle_whiteboard_change)
            
            return whiteboard
        
        return None
    
    def create_whiteboard_content(self, space_id: str, content_type: str, position: Dict[str, float],
                                 size: Dict[str, float], data: Dict[str, Any],
                                 style: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Create content on the shared whiteboard.
        
        Args:
            space_id: ID of the collaborative space
            content_type: Type of content to create
            position: Position dictionary with x, y coordinates
            size: Size dictionary with width, height
            data: Content-specific data
            style: Optional styling information
            
        Returns:
            Content ID if successful, None otherwise
        """
        whiteboard = self.access_shared_whiteboard(space_id)
        if not whiteboard:
            return None
        
        from .shared_whiteboard import ContentType, Position, Size
        
        try:
            # Convert string content type to enum
            content_type_enum = ContentType(content_type.lower())
            
            # Create position and size objects
            pos = Position(x=position['x'], y=position['y'], z=position.get('z', 0))
            sz = Size(width=size['width'], height=size['height'])
            
            # Add content to whiteboard
            content = whiteboard.add_content(
                worker_id=self.worker_id,
                content_type=content_type_enum,
                position=pos,
                size=sz,
                data=data,
                style=style
            )
            
            if content:
                self.logger.debug(f"Created whiteboard content: {content.content_id}")
                return content.content_id
            
        except Exception as e:
            self.logger.error(f"Failed to create whiteboard content: {e}")
        
        return None
    
    def access_shared_files(self, space_id: str):
        """
        Access the shared file system in a collaborative space.
        
        Args:
            space_id: ID of the collaborative space
            
        Returns:
            SharedFileSystem instance or None if not available
        """
        if space_id not in self.collaborative_spaces:
            self.logger.warning(f"Not in collaborative space {space_id}")
            return None
        
        space_info = self.collaborative_spaces[space_id]
        space = space_info.get('space_instance')
        
        if space:
            return space.get_shared_files()
        
        return None
    
    def broadcast_to_space(self, space_id: str, message_type: str, 
                          content: Dict[str, Any]) -> bool:
        """
        Broadcast a message to all participants in a collaborative space.
        
        Args:
            space_id: ID of the collaborative space
            message_type: Type of message to broadcast
            content: Message content
            
        Returns:
            True if message was broadcast successfully
        """
        if space_id not in self.collaborative_spaces:
            self.logger.warning(f"Not in collaborative space {space_id}")
            return False
        
        space_info = self.collaborative_spaces[space_id]
        space = space_info.get('space_instance')
        
        if space:
            try:
                participants_reached = space.broadcast_message(
                    sender_id=self.worker_id,
                    message_type=message_type,
                    content=content
                )
                
                self.logger.debug(f"Broadcast message to {participants_reached} participants in space {space_id}")
                return participants_reached > 0
                
            except Exception as e:
                self.logger.error(f"Failed to broadcast to space {space_id}: {e}")
                return False
        
        return False
    
    def delegate_task_to_worker(self, target_worker_id: str, task_description: str,
                              task_parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Delegate a task to another worker.
        
        Args:
            target_worker_id: ID of the worker to delegate to
            task_description: Description of the task
            task_parameters: Optional task parameters
            
        Returns:
            True if delegation was successful
        """
        message = {
            'message_type': MessageType.TASK_DELEGATION.value,
            'task_description': task_description,
            'task_parameters': task_parameters or {},
            'delegated_by': self.worker_id,
            'delegated_at': datetime.now().isoformat(),
            'requires_response': True
        }
        
        success = self.send_message_to_worker(target_worker_id, message)
        
        if success:
            self.collaboration_stats['tasks_delegated'] += 1
            
            # Track active delegation
            delegation_id = str(uuid.uuid4())
            self.active_collaborations[delegation_id] = {
                'type': 'task_delegation',
                'target_worker': target_worker_id,
                'task_description': task_description,
                'started_at': datetime.now(),
                'status': 'pending'
            }
        
        return success
    
    def request_verification(self, verifier_worker_id: str, output_to_verify: Any,
                           verification_criteria: Optional[Dict[str, Any]] = None) -> bool:
        """
        Request verification of output from a verifier worker.
        
        Args:
            verifier_worker_id: ID of the verifier worker
            output_to_verify: Output that needs verification
            verification_criteria: Optional verification criteria
            
        Returns:
            True if verification request was sent
        """
        message = {
            'message_type': MessageType.VERIFICATION_REQUEST.value,
            'output_to_verify': output_to_verify,
            'verification_criteria': verification_criteria or {},
            'requested_by': self.worker_id,
            'requested_at': datetime.now().isoformat(),
            'requires_response': True
        }
        
        return self.send_message_to_worker(verifier_worker_id, message)
    
    def broadcast_status_update(self, status: str, details: Optional[Dict[str, Any]] = None) -> int:
        """
        Broadcast a status update to other workers.
        
        Args:
            status: Current status
            details: Optional status details
            
        Returns:
            Number of workers the update was sent to
        """
        if not self._is_connected:
            return 0
        
        message = {
            'message_type': MessageType.STATUS_UPDATE.value,
            'status': status,
            'details': details or {},
            'worker_name': self.name,
            'worker_type': self.worker_type.value,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            server = self.server_connection.server_instance
            message_router = server.get_worker_registry()._message_router if hasattr(server.get_worker_registry(), '_message_router') else None
            
            if message_router:
                return message_router.broadcast_message(self.worker_id, message)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Status broadcast failed: {e}")
            return 0
    
    def get_collaboration_statistics(self) -> Dict[str, Any]:
        """
        Get collaboration statistics for this worker.
        
        Returns:
            Dictionary containing collaboration statistics
        """
        return {
            **self.collaboration_stats,
            'active_collaborations': len(self.active_collaborations),
            'collaborative_spaces': len([s for s in self.collaborative_spaces.values() if s['active']]),
            'is_connected': self._is_connected,
            'worker_type': self.worker_type.value,
            'server_connection_active': self.server_connection.is_active if self.server_connection else False
        }
    
    def _get_enhanced_capabilities(self) -> List[str]:
        """Get enhanced capabilities list for this worker."""
        base_capabilities = self._get_capabilities() if hasattr(self, '_get_capabilities') else []
        
        # Add collaborative capabilities
        collaborative_capabilities = [
            'inter_worker_communication',
            'task_delegation',
            'collaborative_spaces',
            'real_time_messaging'
        ]
        
        # Add type-specific capabilities
        type_capabilities = {
            WorkerType.PLANNER: ['strategy_creation', 'worker_management', 'flowchart_design'],
            WorkerType.EXECUTOR: ['task_execution', 'tool_usage', 'progress_reporting'],
            WorkerType.VERIFIER: ['quality_validation', 'output_verification', 'feedback_generation']
        }
        
        return base_capabilities + collaborative_capabilities + type_capabilities.get(self.worker_type, [])
    
    def _get_detailed_capabilities(self) -> List[Dict[str, Any]]:
        """Get detailed capability information."""
        capabilities = []
        
        # Add type-specific detailed capabilities
        if self.worker_type == WorkerType.PLANNER:
            capabilities.extend([
                {'name': 'strategy_creation', 'level': 8, 'description': 'Create execution strategies'},
                {'name': 'worker_management', 'level': 7, 'description': 'Manage and coordinate workers'},
                {'name': 'task_planning', 'level': 9, 'description': 'Plan complex task workflows'}
            ])
        elif self.worker_type == WorkerType.EXECUTOR:
            capabilities.extend([
                {'name': 'task_execution', 'level': 8, 'description': 'Execute assigned tasks'},
                {'name': 'tool_usage', 'level': 7, 'description': 'Use various tools and integrations'},
                {'name': 'problem_solving', 'level': 8, 'description': 'Solve complex problems'}
            ])
        elif self.worker_type == WorkerType.VERIFIER:
            capabilities.extend([
                {'name': 'quality_validation', 'level': 9, 'description': 'Validate output quality'},
                {'name': 'error_detection', 'level': 8, 'description': 'Detect errors and issues'},
                {'name': 'feedback_generation', 'level': 7, 'description': 'Generate improvement feedback'}
            ])
        
        # Add collaborative capabilities
        capabilities.extend([
            {'name': 'collaboration', 'level': 8, 'description': 'Work effectively with other workers'},
            {'name': 'communication', 'level': 7, 'description': 'Communicate clearly and effectively'}
        ])
        
        return capabilities
    
    def _setup_default_message_handlers(self) -> None:
        """Setup default message handlers for different message types."""
        self.message_handlers = {
            MessageType.TASK_DELEGATION: self._handle_task_delegation,
            MessageType.VERIFICATION_REQUEST: self._handle_verification_request,
            MessageType.COLLABORATION_INVITE: self._handle_collaboration_invite,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.RESULT_REPORT: self._handle_result_report,
            MessageType.ERROR_NOTIFICATION: self._handle_error_notification,
            MessageType.BROADCAST: self._handle_broadcast_message
        }
    
    def _handle_incoming_message(self, message: CollaborativeMessage) -> None:
        """Handle incoming messages from other workers."""
        try:
            with self._message_lock:
                self._message_queue.append(message)
                self.collaboration_stats['messages_received'] += 1
            
            # Get appropriate handler
            handler = self.message_handlers.get(message.message_type)
            
            if handler:
                handler(message)
            else:
                self.logger.warning(f"No handler for message type: {message.message_type}")
            
        except Exception as e:
            self.logger.error(f"Message handling failed: {e}")
    
    def _handle_task_delegation(self, message: CollaborativeMessage) -> None:
        """Handle task delegation messages."""
        self.collaboration_stats['tasks_received'] += 1
        
        # Extract task information
        task_description = message.content.get('task_description', '')
        task_parameters = message.content.get('task_parameters', {})
        
        self.logger.info(f"Received task delegation: {task_description}")
        
        # For now, just log the delegation
        # Actual task execution will be implemented in specialized worker classes
    
    def _handle_verification_request(self, message: CollaborativeMessage) -> None:
        """Handle verification request messages."""
        output_to_verify = message.content.get('output_to_verify')
        verification_criteria = message.content.get('verification_criteria', {})
        
        self.logger.info(f"Received verification request from {message.from_worker_id}")
        
        # For now, just log the request
        # Actual verification will be implemented in VerifierWorker class
    
    def _handle_collaboration_invite(self, message: CollaborativeMessage) -> None:
        """Handle collaboration invite messages."""
        space_id = message.content.get('collaborative_space_id')
        
        if space_id:
            self.join_collaborative_space(space_id)
    
    def _handle_status_update(self, message: CollaborativeMessage) -> None:
        """Handle status update messages."""
        status = message.content.get('status', '')
        worker_name = message.content.get('worker_name', 'Unknown')
        
        self.logger.debug(f"Status update from {worker_name}: {status}")
    
    def _handle_result_report(self, message: CollaborativeMessage) -> None:
        """Handle result report messages."""
        # Update collaboration tracking
        for collab_id, collab in self.active_collaborations.items():
            if collab.get('target_worker') == message.from_worker_id:
                collab['status'] = 'completed'
                collab['completed_at'] = datetime.now()
                break
    
    def _handle_error_notification(self, message: CollaborativeMessage) -> None:
        """Handle error notification messages."""
        error_details = message.content.get('error_details', {})
        self.logger.warning(f"Error notification from {message.from_worker_id}: {error_details}")
    
    def _handle_broadcast_message(self, message: CollaborativeMessage) -> None:
        """Handle broadcast messages."""
        self.logger.debug(f"Broadcast message from {message.from_worker_id}")
    
    def _handle_space_message(self, message) -> None:
        """
        Handle messages from collaborative spaces.
        
        Args:
            message: SpaceMessage instance from collaborative space
        """
        try:
            self.logger.debug(f"Space message from {message.sender_name} in space {message.space_id}: {message.message_type}")
            
            # Update activity for the space
            if message.space_id in self.collaborative_spaces:
                space_info = self.collaborative_spaces[message.space_id]
                space = space_info.get('space_instance')
                if space:
                    space.update_participant_activity(self.worker_id)
            
            # Handle specific message types
            if message.message_type == "participant_joined":
                self.logger.info(f"New participant joined space {message.space_id}: {message.content.get('worker_name')}")
            elif message.message_type == "participant_left":
                self.logger.info(f"Participant left space {message.space_id}: {message.content.get('worker_name')}")
            elif message.message_type == "space_paused":
                self.logger.info(f"Space {message.space_id} has been paused")
            elif message.message_type == "space_resumed":
                self.logger.info(f"Space {message.space_id} has been resumed")
            elif message.message_type == "space_closed":
                self.logger.info(f"Space {message.space_id} has been closed")
                # Remove from local tracking
                if message.space_id in self.collaborative_spaces:
                    self.collaborative_spaces[message.space_id]['active'] = False
            
        except Exception as e:
            self.logger.error(f"Error handling space message: {e}")
    
    def _handle_whiteboard_change(self, notification: Dict[str, Any]) -> None:
        """
        Handle whiteboard change notifications.
        
        Args:
            notification: Whiteboard change notification
        """
        try:
            change_type = notification.get('type', 'unknown')
            worker_id = notification.get('worker_id', 'unknown')
            
            if worker_id != self.worker_id:  # Don't log our own changes
                if change_type == 'content_added':
                    content = notification.get('content', {})
                    self.logger.debug(f"Whiteboard content added by {worker_id}: {content.get('content_type')}")
                elif change_type == 'content_updated':
                    content = notification.get('content', {})
                    self.logger.debug(f"Whiteboard content updated by {worker_id}: {content.get('content_id')}")
                elif change_type == 'content_deleted':
                    content_id = notification.get('content_id')
                    self.logger.debug(f"Whiteboard content deleted by {worker_id}: {content_id}")
                elif change_type == 'whiteboard_cleared':
                    self.logger.info(f"Whiteboard cleared by {worker_id}")
                elif change_type == 'content_locked':
                    content_id = notification.get('content_id')
                    self.logger.debug(f"Whiteboard content locked by {worker_id}: {content_id}")
                elif change_type == 'content_unlocked':
                    content_id = notification.get('content_id')
                    self.logger.debug(f"Whiteboard content unlocked by {worker_id}: {content_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling whiteboard change: {e}")
    
    def shutdown(self) -> None:
        """Shutdown the enhanced worker."""
        # Disconnect from server
        self.disconnect_from_server()
        
        # Clear collaborative data
        self.collaborative_spaces.clear()
        self.active_collaborations.clear()
        
        # Call parent shutdown
        if hasattr(super(), 'shutdown'):
            super().shutdown()
        
        self.logger.info(f"Enhanced worker {self.name} shutdown complete")
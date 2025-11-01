"""
Collaborative Space Management System

Provides virtual environments where multiple workers can collaborate on shared tasks
with real-time communication and resource sharing capabilities.
"""

import uuid
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import logging


class ParticipantRole(Enum):
    """Roles that participants can have in a collaborative space"""
    OWNER = "owner"
    MODERATOR = "moderator"
    PARTICIPANT = "participant"
    OBSERVER = "observer"


class SpaceState(Enum):
    """States of a collaborative space"""
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    CLOSED = "closed"


@dataclass
class Participant:
    """Represents a participant in a collaborative space"""
    worker_id: str
    worker_name: str
    worker_type: str
    role: ParticipantRole
    joined_at: datetime
    last_activity: datetime
    is_active: bool = True
    permissions: Set[str] = field(default_factory=set)


@dataclass
class SpaceMessage:
    """Message within a collaborative space"""
    message_id: str
    sender_id: str
    sender_name: str
    content: Dict[str, Any]
    message_type: str
    timestamp: datetime
    space_id: str
    requires_response: bool = False
    response_to: Optional[str] = None


class CollaborativeSpace:
    """
    Virtual environment for worker collaboration.
    
    Provides:
    - Participant management and permissions
    - Space-specific message broadcasting
    - Real-time synchronization of participants
    - Resource access coordination
    """
    
    def __init__(self, space_id: str, name: str, created_by: str, 
                 description: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize a collaborative space.
        
        Args:
            space_id: Unique identifier for the space
            name: Human-readable name for the space
            created_by: Worker ID of the space creator
            description: Optional description of the space purpose
            config: Optional configuration parameters
        """
        self.space_id = space_id
        self.name = name
        self.description = description or ""
        self.created_by = created_by
        self.created_at = datetime.now()
        self.config = config or {}
        
        # Space state
        self.state = SpaceState.ACTIVE
        self.last_activity = datetime.now()
        
        # Participant management
        self.participants: Dict[str, Participant] = {}
        self.participant_lock = threading.RLock()
        
        # Message history and broadcasting
        self.message_history: List[SpaceMessage] = []
        self.message_lock = threading.RLock()
        self.message_subscribers: Dict[str, Callable] = {}
        
        # Shared resources (will be populated by other components)
        self.shared_whiteboard = None
        self.shared_files = None
        
        # Activity tracking
        self.activity_log: List[Dict[str, Any]] = []
        self.statistics = {
            'total_participants': 0,
            'messages_sent': 0,
            'resources_created': 0,
            'collaborations_completed': 0
        }
        
        # Setup logging
        self.logger = logging.getLogger(f"CollaborativeSpace.{space_id[:8]}")
        
        self.logger.info(f"Collaborative space '{name}' created by {created_by}")
    
    def add_participant(self, worker_id: str, worker_name: str, worker_type: str,
                       role: ParticipantRole = ParticipantRole.PARTICIPANT,
                       permissions: Optional[Set[str]] = None) -> bool:
        """
        Add a participant to the collaborative space.
        
        Args:
            worker_id: Unique identifier of the worker
            worker_name: Human-readable name of the worker
            worker_type: Type of worker (Planner, Executor, Verifier)
            role: Role of the participant in the space
            permissions: Optional set of permissions for the participant
            
        Returns:
            True if participant was added successfully
        """
        with self.participant_lock:
            if worker_id in self.participants:
                self.logger.warning(f"Worker {worker_id} already in space {self.space_id}")
                return False
            
            # Create participant
            participant = Participant(
                worker_id=worker_id,
                worker_name=worker_name,
                worker_type=worker_type,
                role=role,
                joined_at=datetime.now(),
                last_activity=datetime.now(),
                permissions=permissions or self._get_default_permissions(role)
            )
            
            self.participants[worker_id] = participant
            self.statistics['total_participants'] += 1
            
            # Log activity
            self._log_activity({
                'type': 'participant_joined',
                'worker_id': worker_id,
                'worker_name': worker_name,
                'role': role.value,
                'timestamp': datetime.now()
            })
            
            # Notify other participants
            self._broadcast_space_message(
                sender_id="system",
                sender_name="System",
                message_type="participant_joined",
                content={
                    'worker_id': worker_id,
                    'worker_name': worker_name,
                    'worker_type': worker_type,
                    'role': role.value
                }
            )
            
            self.logger.info(f"Participant {worker_name} ({worker_id}) joined space {self.space_id}")
            return True
    
    def remove_participant(self, worker_id: str, reason: str = "left") -> bool:
        """
        Remove a participant from the collaborative space.
        
        Args:
            worker_id: ID of the worker to remove
            reason: Reason for removal
            
        Returns:
            True if participant was removed successfully
        """
        with self.participant_lock:
            if worker_id not in self.participants:
                self.logger.warning(f"Worker {worker_id} not in space {self.space_id}")
                return False
            
            participant = self.participants[worker_id]
            participant.is_active = False
            
            # Log activity
            self._log_activity({
                'type': 'participant_left',
                'worker_id': worker_id,
                'worker_name': participant.worker_name,
                'reason': reason,
                'timestamp': datetime.now()
            })
            
            # Notify other participants
            self._broadcast_space_message(
                sender_id="system",
                sender_name="System",
                message_type="participant_left",
                content={
                    'worker_id': worker_id,
                    'worker_name': participant.worker_name,
                    'reason': reason
                }
            )
            
            # Remove from active participants
            del self.participants[worker_id]
            
            self.logger.info(f"Participant {participant.worker_name} ({worker_id}) left space {self.space_id}")
            return True
    
    def get_participants(self, active_only: bool = True) -> List[Participant]:
        """
        Get list of participants in the space.
        
        Args:
            active_only: If True, only return active participants
            
        Returns:
            List of participants
        """
        with self.participant_lock:
            participants = list(self.participants.values())
            
            if active_only:
                participants = [p for p in participants if p.is_active]
            
            return participants
    
    def get_participant(self, worker_id: str) -> Optional[Participant]:
        """
        Get a specific participant by worker ID.
        
        Args:
            worker_id: ID of the worker
            
        Returns:
            Participant object or None if not found
        """
        with self.participant_lock:
            return self.participants.get(worker_id)
    
    def update_participant_activity(self, worker_id: str) -> None:
        """
        Update the last activity timestamp for a participant.
        
        Args:
            worker_id: ID of the worker
        """
        with self.participant_lock:
            if worker_id in self.participants:
                self.participants[worker_id].last_activity = datetime.now()
                self.last_activity = datetime.now()
    
    def broadcast_message(self, sender_id: str, message_type: str, 
                         content: Dict[str, Any], requires_response: bool = False) -> int:
        """
        Broadcast a message to all participants in the space.
        
        Args:
            sender_id: ID of the message sender
            message_type: Type of message being sent
            content: Message content
            requires_response: Whether the message requires a response
            
        Returns:
            Number of participants the message was sent to
        """
        sender = self.get_participant(sender_id)
        sender_name = sender.worker_name if sender else "Unknown"
        
        return self._broadcast_space_message(
            sender_id=sender_id,
            sender_name=sender_name,
            message_type=message_type,
            content=content,
            requires_response=requires_response
        )
    
    def send_direct_message(self, sender_id: str, recipient_id: str, 
                           message_type: str, content: Dict[str, Any]) -> bool:
        """
        Send a direct message to a specific participant.
        
        Args:
            sender_id: ID of the message sender
            recipient_id: ID of the message recipient
            message_type: Type of message
            content: Message content
            
        Returns:
            True if message was sent successfully
        """
        # Check if both sender and recipient are in the space
        if sender_id not in self.participants or recipient_id not in self.participants:
            self.logger.warning(f"Direct message failed: sender or recipient not in space")
            return False
        
        sender = self.participants[sender_id]
        
        # Create message
        message = SpaceMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_name=sender.worker_name,
            content=content,
            message_type=message_type,
            timestamp=datetime.now(),
            space_id=self.space_id
        )
        
        # Store in message history
        with self.message_lock:
            self.message_history.append(message)
            self.statistics['messages_sent'] += 1
        
        # Deliver to recipient if they have a subscriber
        if recipient_id in self.message_subscribers:
            try:
                self.message_subscribers[recipient_id](message)
                self.logger.debug(f"Direct message sent: {sender_id} -> {recipient_id}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to deliver direct message: {e}")
                return False
        
        return True
    
    def subscribe_to_messages(self, worker_id: str, callback: Callable[[SpaceMessage], None]) -> bool:
        """
        Subscribe to receive messages in this space.
        
        Args:
            worker_id: ID of the worker subscribing
            callback: Function to call when messages are received
            
        Returns:
            True if subscription was successful
        """
        if worker_id not in self.participants:
            self.logger.warning(f"Cannot subscribe worker {worker_id} - not a participant")
            return False
        
        self.message_subscribers[worker_id] = callback
        self.logger.debug(f"Worker {worker_id} subscribed to space messages")
        return True
    
    def unsubscribe_from_messages(self, worker_id: str) -> None:
        """
        Unsubscribe from receiving messages in this space.
        
        Args:
            worker_id: ID of the worker unsubscribing
        """
        if worker_id in self.message_subscribers:
            del self.message_subscribers[worker_id]
            self.logger.debug(f"Worker {worker_id} unsubscribed from space messages")
    
    def get_message_history(self, limit: Optional[int] = None, 
                           since: Optional[datetime] = None) -> List[SpaceMessage]:
        """
        Get message history for the space.
        
        Args:
            limit: Maximum number of messages to return
            since: Only return messages after this timestamp
            
        Returns:
            List of messages
        """
        with self.message_lock:
            messages = self.message_history.copy()
            
            # Filter by timestamp if specified
            if since:
                messages = [m for m in messages if m.timestamp > since]
            
            # Sort by timestamp (newest first)
            messages.sort(key=lambda m: m.timestamp, reverse=True)
            
            # Apply limit if specified
            if limit:
                messages = messages[:limit]
            
            return messages
    
    def get_space_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the collaborative space.
        
        Returns:
            Dictionary containing space statistics
        """
        active_participants = len([p for p in self.participants.values() if p.is_active])
        
        return {
            **self.statistics,
            'space_id': self.space_id,
            'name': self.name,
            'state': self.state.value,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'active_participants': active_participants,
            'total_messages': len(self.message_history),
            'has_shared_whiteboard': self.shared_whiteboard is not None,
            'has_shared_files': self.shared_files is not None
        }
    
    def create_shared_whiteboard(self, name: str = "Shared Whiteboard",
                                config: Optional[Dict[str, Any]] = None) -> 'SharedWhiteboard':
        """
        Create a shared whiteboard for this space.
        
        Args:
            name: Name for the whiteboard
            config: Optional configuration parameters
            
        Returns:
            Created SharedWhiteboard instance
        """
        from .shared_whiteboard import SharedWhiteboard
        
        whiteboard_id = f"{self.space_id}_whiteboard_{str(uuid.uuid4())[:8]}"
        
        self.shared_whiteboard = SharedWhiteboard(
            whiteboard_id=whiteboard_id,
            space_id=self.space_id,
            name=name,
            config=config
        )
        
        self.statistics['resources_created'] += 1
        
        self._log_activity({
            'type': 'shared_whiteboard_created',
            'whiteboard_id': whiteboard_id,
            'name': name,
            'timestamp': datetime.now()
        })
        
        # Notify participants
        self._broadcast_space_message(
            sender_id="system",
            sender_name="System",
            message_type="shared_whiteboard_created",
            content={
                'whiteboard_id': whiteboard_id,
                'name': name
            }
        )
        
        return self.shared_whiteboard
    
    def set_shared_whiteboard(self, whiteboard) -> None:
        """
        Set the shared whiteboard for this space.
        
        Args:
            whiteboard: SharedWhiteboard instance
        """
        self.shared_whiteboard = whiteboard
        self.statistics['resources_created'] += 1
        
        self._log_activity({
            'type': 'shared_whiteboard_set',
            'timestamp': datetime.now()
        })
    
    def get_shared_whiteboard(self):
        """
        Get the shared whiteboard for this space.
        
        Returns:
            SharedWhiteboard instance or None
        """
        return self.shared_whiteboard
    
    def set_shared_files(self, file_system) -> None:
        """
        Set the shared file system for this space.
        
        Args:
            file_system: SharedFileSystem instance
        """
        self.shared_files = file_system
        self.statistics['resources_created'] += 1
        
        self._log_activity({
            'type': 'shared_files_created',
            'timestamp': datetime.now()
        })
    
    def get_shared_files(self):
        """
        Get the shared file system for this space.
        
        Returns:
            SharedFileSystem instance or None
        """
        return self.shared_files
    
    def pause_space(self) -> None:
        """Pause the collaborative space."""
        self.state = SpaceState.PAUSED
        self._log_activity({
            'type': 'space_paused',
            'timestamp': datetime.now()
        })
        
        self._broadcast_space_message(
            sender_id="system",
            sender_name="System",
            message_type="space_paused",
            content={'reason': 'Space has been paused'}
        )
    
    def resume_space(self) -> None:
        """Resume the collaborative space."""
        self.state = SpaceState.ACTIVE
        self._log_activity({
            'type': 'space_resumed',
            'timestamp': datetime.now()
        })
        
        self._broadcast_space_message(
            sender_id="system",
            sender_name="System",
            message_type="space_resumed",
            content={'reason': 'Space has been resumed'}
        )
    
    def close_space(self) -> None:
        """Close the collaborative space."""
        self.state = SpaceState.CLOSED
        
        # Notify all participants
        self._broadcast_space_message(
            sender_id="system",
            sender_name="System",
            message_type="space_closed",
            content={'reason': 'Space has been closed'}
        )
        
        # Clear subscribers
        self.message_subscribers.clear()
        
        self._log_activity({
            'type': 'space_closed',
            'timestamp': datetime.now()
        })
        
        self.logger.info(f"Collaborative space {self.space_id} closed")
    
    def _broadcast_space_message(self, sender_id: str, sender_name: str, 
                                message_type: str, content: Dict[str, Any],
                                requires_response: bool = False) -> int:
        """
        Internal method to broadcast messages to all participants.
        
        Returns:
            Number of participants the message was delivered to
        """
        # Create message
        message = SpaceMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            message_type=message_type,
            timestamp=datetime.now(),
            space_id=self.space_id,
            requires_response=requires_response
        )
        
        # Store in message history
        with self.message_lock:
            self.message_history.append(message)
            if sender_id != "system":
                self.statistics['messages_sent'] += 1
        
        # Deliver to all subscribers
        delivered_count = 0
        for worker_id, callback in self.message_subscribers.items():
            if worker_id != sender_id:  # Don't send to sender
                try:
                    callback(message)
                    delivered_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to deliver message to {worker_id}: {e}")
        
        # Update activity
        self.last_activity = datetime.now()
        if sender_id in self.participants:
            self.update_participant_activity(sender_id)
        
        return delivered_count
    
    def _get_default_permissions(self, role: ParticipantRole) -> Set[str]:
        """Get default permissions for a participant role."""
        permissions = {
            ParticipantRole.OWNER: {
                'manage_participants', 'send_messages', 'access_whiteboard', 
                'access_files', 'modify_space', 'close_space'
            },
            ParticipantRole.MODERATOR: {
                'manage_participants', 'send_messages', 'access_whiteboard', 
                'access_files', 'modify_space'
            },
            ParticipantRole.PARTICIPANT: {
                'send_messages', 'access_whiteboard', 'access_files'
            },
            ParticipantRole.OBSERVER: {
                'access_whiteboard', 'access_files'
            }
        }
        
        return permissions.get(role, set())
    
    def _log_activity(self, activity: Dict[str, Any]) -> None:
        """Log an activity in the space."""
        self.activity_log.append(activity)
        
        # Keep only last 1000 activities to prevent memory issues
        if len(self.activity_log) > 1000:
            self.activity_log = self.activity_log[-1000:]


class CollaborativeSpaceManager:
    """
    Manager for creating and coordinating collaborative spaces.
    
    Provides centralized management of all collaborative spaces
    and handles space lifecycle operations.
    """
    
    def __init__(self):
        """Initialize the collaborative space manager."""
        self.spaces: Dict[str, CollaborativeSpace] = {}
        self.spaces_lock = threading.RLock()
        
        # Statistics
        self.statistics = {
            'total_spaces_created': 0,
            'active_spaces': 0,
            'total_participants': 0,
            'total_messages': 0
        }
        
        self.logger = logging.getLogger("CollaborativeSpaceManager")
        self.logger.info("Collaborative space manager initialized")
    
    def create_space(self, name: str, created_by: str, 
                    description: Optional[str] = None,
                    config: Optional[Dict[str, Any]] = None,
                    space_id: Optional[str] = None) -> CollaborativeSpace:
        """
        Create a new collaborative space.
        
        Args:
            name: Human-readable name for the space
            created_by: Worker ID of the space creator
            description: Optional description of the space
            config: Optional configuration parameters
            space_id: Optional custom space ID
            
        Returns:
            Created CollaborativeSpace instance
        """
        if space_id is None:
            space_id = str(uuid.uuid4())
        
        with self.spaces_lock:
            if space_id in self.spaces:
                raise ValueError(f"Space with ID {space_id} already exists")
            
            # Create the space
            space = CollaborativeSpace(
                space_id=space_id,
                name=name,
                created_by=created_by,
                description=description,
                config=config
            )
            
            # Add creator as owner
            space.add_participant(
                worker_id=created_by,
                worker_name=f"Worker-{created_by[:8]}",  # Will be updated with actual name
                worker_type="Unknown",  # Will be updated with actual type
                role=ParticipantRole.OWNER
            )
            
            self.spaces[space_id] = space
            self.statistics['total_spaces_created'] += 1
            self.statistics['active_spaces'] += 1
            
            self.logger.info(f"Created collaborative space '{name}' ({space_id}) by {created_by}")
            return space
    
    def get_space(self, space_id: str) -> Optional[CollaborativeSpace]:
        """
        Get a collaborative space by ID.
        
        Args:
            space_id: ID of the space to retrieve
            
        Returns:
            CollaborativeSpace instance or None if not found
        """
        with self.spaces_lock:
            return self.spaces.get(space_id)
    
    def list_spaces(self, active_only: bool = True) -> List[CollaborativeSpace]:
        """
        List all collaborative spaces.
        
        Args:
            active_only: If True, only return active spaces
            
        Returns:
            List of collaborative spaces
        """
        with self.spaces_lock:
            spaces = list(self.spaces.values())
            
            if active_only:
                spaces = [s for s in spaces if s.state == SpaceState.ACTIVE]
            
            return spaces
    
    def close_space(self, space_id: str) -> bool:
        """
        Close a collaborative space.
        
        Args:
            space_id: ID of the space to close
            
        Returns:
            True if space was closed successfully
        """
        with self.spaces_lock:
            space = self.spaces.get(space_id)
            if not space:
                return False
            
            space.close_space()
            
            if space.state == SpaceState.ACTIVE:
                self.statistics['active_spaces'] -= 1
            
            self.logger.info(f"Closed collaborative space {space_id}")
            return True
    
    def get_spaces_for_worker(self, worker_id: str) -> List[CollaborativeSpace]:
        """
        Get all spaces that a worker is participating in.
        
        Args:
            worker_id: ID of the worker
            
        Returns:
            List of collaborative spaces the worker is in
        """
        with self.spaces_lock:
            worker_spaces = []
            
            for space in self.spaces.values():
                if worker_id in space.participants:
                    worker_spaces.append(space)
            
            return worker_spaces
    
    def get_manager_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all collaborative spaces.
        
        Returns:
            Dictionary containing manager statistics
        """
        with self.spaces_lock:
            # Calculate current statistics
            active_spaces = len([s for s in self.spaces.values() if s.state == SpaceState.ACTIVE])
            total_participants = sum(len(s.participants) for s in self.spaces.values())
            total_messages = sum(len(s.message_history) for s in self.spaces.values())
            
            return {
                **self.statistics,
                'active_spaces': active_spaces,
                'total_participants': total_participants,
                'total_messages': total_messages,
                'total_spaces': len(self.spaces)
            }
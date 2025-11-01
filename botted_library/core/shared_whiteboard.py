"""
Shared Whiteboard System for Collaborative Spaces

Provides real-time collaborative whiteboard functionality where multiple workers
can share visual information, diagrams, and content with automatic synchronization.
"""

import uuid
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import json


class ContentType(Enum):
    """Types of content that can be added to the whiteboard"""
    TEXT = "text"
    DRAWING = "drawing"
    SHAPE = "shape"
    IMAGE = "image"
    DIAGRAM = "diagram"
    NOTE = "note"
    FLOWCHART = "flowchart"
    MINDMAP = "mindmap"


class ContentOperation(Enum):
    """Operations that can be performed on whiteboard content"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    RESIZE = "resize"
    STYLE_CHANGE = "style_change"


@dataclass
class Position:
    """Position coordinates on the whiteboard"""
    x: float
    y: float
    z: int = 0  # Z-index for layering


@dataclass
class Size:
    """Size dimensions for whiteboard content"""
    width: float
    height: float


@dataclass
class WhiteboardContent:
    """Represents a piece of content on the whiteboard"""
    content_id: str
    content_type: ContentType
    position: Position
    size: Size
    data: Dict[str, Any]
    style: Dict[str, Any]
    created_by: str
    created_at: datetime
    last_modified_by: str
    last_modified_at: datetime
    version: int = 1
    is_locked: bool = False
    locked_by: Optional[str] = None
    tags: Set[str] = field(default_factory=set)


@dataclass
class ContentChange:
    """Represents a change made to whiteboard content"""
    change_id: str
    content_id: str
    operation: ContentOperation
    old_data: Optional[Dict[str, Any]]
    new_data: Dict[str, Any]
    changed_by: str
    timestamp: datetime
    description: str


class SharedWhiteboard:
    """
    Collaborative whiteboard with real-time synchronization.
    
    Provides:
    - Multi-user content creation and editing
    - Real-time synchronization between participants
    - Content versioning and change tracking
    - Locking mechanism to prevent conflicts
    - Change notifications and subscriptions
    """
    
    def __init__(self, whiteboard_id: str, space_id: str, name: str = "Shared Whiteboard",
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize a shared whiteboard.
        
        Args:
            whiteboard_id: Unique identifier for the whiteboard
            space_id: ID of the collaborative space this whiteboard belongs to
            name: Human-readable name for the whiteboard
            config: Optional configuration parameters
        """
        self.whiteboard_id = whiteboard_id
        self.space_id = space_id
        self.name = name
        self.config = config or {}
        self.created_at = datetime.now()
        
        # Content management
        self.contents: Dict[str, WhiteboardContent] = {}
        self.content_lock = threading.RLock()
        
        # Change tracking
        self.change_history: List[ContentChange] = []
        self.change_lock = threading.RLock()
        
        # Real-time synchronization
        self.subscribers: Dict[str, Callable] = {}
        self.subscriber_lock = threading.RLock()
        
        # Content locking for conflict prevention
        self.content_locks: Dict[str, str] = {}  # content_id -> worker_id
        self.lock_timeout = self.config.get('lock_timeout', 300)  # 5 minutes default
        
        # Statistics
        self.statistics = {
            'total_content_items': 0,
            'total_changes': 0,
            'active_subscribers': 0,
            'locked_items': 0
        }
        
        # Setup logging
        self.logger = logging.getLogger(f"SharedWhiteboard.{whiteboard_id[:8]}")
        self.logger.info(f"Shared whiteboard '{name}' initialized for space {space_id}")
    
    def add_content(self, worker_id: str, content_type: ContentType, position: Position,
                   size: Size, data: Dict[str, Any], style: Optional[Dict[str, Any]] = None,
                   content_id: Optional[str] = None) -> Optional[WhiteboardContent]:
        """
        Add new content to the whiteboard.
        
        Args:
            worker_id: ID of the worker adding the content
            content_type: Type of content being added
            position: Position on the whiteboard
            size: Size of the content
            data: Content-specific data
            style: Optional styling information
            content_id: Optional custom content ID
            
        Returns:
            Created WhiteboardContent instance or None if failed
        """
        if content_id is None:
            content_id = str(uuid.uuid4())
        
        with self.content_lock:
            if content_id in self.contents:
                self.logger.warning(f"Content with ID {content_id} already exists")
                return None
            
            # Create content
            content = WhiteboardContent(
                content_id=content_id,
                content_type=content_type,
                position=position,
                size=size,
                data=data,
                style=style or {},
                created_by=worker_id,
                created_at=datetime.now(),
                last_modified_by=worker_id,
                last_modified_at=datetime.now()
            )
            
            self.contents[content_id] = content
            self.statistics['total_content_items'] += 1
            
            # Record change
            change = self._record_change(
                content_id=content_id,
                operation=ContentOperation.CREATE,
                old_data=None,
                new_data=self._serialize_content(content),
                changed_by=worker_id,
                description=f"Created {content_type.value} content"
            )
            
            # Notify subscribers
            self._notify_subscribers({
                'type': 'content_added',
                'content': self._serialize_content(content),
                'change': self._serialize_change(change),
                'worker_id': worker_id
            })
            
            self.logger.debug(f"Content added by {worker_id}: {content_type.value} at ({position.x}, {position.y})")
            return content
    
    def update_content(self, worker_id: str, content_id: str, 
                      updates: Dict[str, Any]) -> bool:
        """
        Update existing content on the whiteboard.
        
        Args:
            worker_id: ID of the worker making the update
            content_id: ID of the content to update
            updates: Dictionary of fields to update
            
        Returns:
            True if update was successful
        """
        with self.content_lock:
            if content_id not in self.contents:
                self.logger.warning(f"Content {content_id} not found")
                return False
            
            # Check if content is locked by another worker
            if self._is_content_locked(content_id, worker_id):
                self.logger.warning(f"Content {content_id} is locked by another worker")
                return False
            
            content = self.contents[content_id]
            old_data = self._serialize_content(content)
            
            # Apply updates
            if 'position' in updates:
                pos_data = updates['position']
                content.position = Position(
                    x=pos_data.get('x', content.position.x),
                    y=pos_data.get('y', content.position.y),
                    z=pos_data.get('z', content.position.z)
                )
            
            if 'size' in updates:
                size_data = updates['size']
                content.size = Size(
                    width=size_data.get('width', content.size.width),
                    height=size_data.get('height', content.size.height)
                )
            
            if 'data' in updates:
                content.data.update(updates['data'])
            
            if 'style' in updates:
                content.style.update(updates['style'])
            
            if 'tags' in updates:
                content.tags = set(updates['tags'])
            
            # Update metadata
            content.last_modified_by = worker_id
            content.last_modified_at = datetime.now()
            content.version += 1
            
            # Record change
            change = self._record_change(
                content_id=content_id,
                operation=ContentOperation.UPDATE,
                old_data=old_data,
                new_data=self._serialize_content(content),
                changed_by=worker_id,
                description=f"Updated {content.content_type.value} content"
            )
            
            # Notify subscribers
            self._notify_subscribers({
                'type': 'content_updated',
                'content': self._serialize_content(content),
                'change': self._serialize_change(change),
                'worker_id': worker_id,
                'updates': updates
            })
            
            self.logger.debug(f"Content updated by {worker_id}: {content_id}")
            return True
    
    def delete_content(self, worker_id: str, content_id: str) -> bool:
        """
        Delete content from the whiteboard.
        
        Args:
            worker_id: ID of the worker deleting the content
            content_id: ID of the content to delete
            
        Returns:
            True if deletion was successful
        """
        with self.content_lock:
            if content_id not in self.contents:
                self.logger.warning(f"Content {content_id} not found")
                return False
            
            # Check if content is locked by another worker
            if self._is_content_locked(content_id, worker_id):
                self.logger.warning(f"Content {content_id} is locked by another worker")
                return False
            
            content = self.contents[content_id]
            old_data = self._serialize_content(content)
            
            # Remove content
            del self.contents[content_id]
            self.statistics['total_content_items'] -= 1
            
            # Remove any locks
            if content_id in self.content_locks:
                del self.content_locks[content_id]
                self.statistics['locked_items'] -= 1
            
            # Record change
            change = self._record_change(
                content_id=content_id,
                operation=ContentOperation.DELETE,
                old_data=old_data,
                new_data=None,
                changed_by=worker_id,
                description=f"Deleted {content.content_type.value} content"
            )
            
            # Notify subscribers
            self._notify_subscribers({
                'type': 'content_deleted',
                'content_id': content_id,
                'change': self._serialize_change(change),
                'worker_id': worker_id
            })
            
            self.logger.debug(f"Content deleted by {worker_id}: {content_id}")
            return True
    
    def get_content(self, content_id: str) -> Optional[WhiteboardContent]:
        """
        Get a specific piece of content by ID.
        
        Args:
            content_id: ID of the content to retrieve
            
        Returns:
            WhiteboardContent instance or None if not found
        """
        with self.content_lock:
            return self.contents.get(content_id)
    
    def get_all_content(self, content_type: Optional[ContentType] = None,
                       created_by: Optional[str] = None) -> List[WhiteboardContent]:
        """
        Get all content on the whiteboard with optional filtering.
        
        Args:
            content_type: Optional filter by content type
            created_by: Optional filter by creator
            
        Returns:
            List of WhiteboardContent instances
        """
        with self.content_lock:
            contents = list(self.contents.values())
            
            # Apply filters
            if content_type:
                contents = [c for c in contents if c.content_type == content_type]
            
            if created_by:
                contents = [c for c in contents if c.created_by == created_by]
            
            # Sort by creation time
            contents.sort(key=lambda c: c.created_at)
            
            return contents
    
    def lock_content(self, worker_id: str, content_id: str) -> bool:
        """
        Lock content to prevent concurrent modifications.
        
        Args:
            worker_id: ID of the worker requesting the lock
            content_id: ID of the content to lock
            
        Returns:
            True if lock was acquired successfully
        """
        with self.content_lock:
            if content_id not in self.contents:
                return False
            
            # Check if already locked
            if content_id in self.content_locks:
                if self.content_locks[content_id] == worker_id:
                    return True  # Already locked by this worker
                else:
                    return False  # Locked by another worker
            
            # Acquire lock
            self.content_locks[content_id] = worker_id
            self.contents[content_id].is_locked = True
            self.contents[content_id].locked_by = worker_id
            self.statistics['locked_items'] += 1
            
            # Notify subscribers
            self._notify_subscribers({
                'type': 'content_locked',
                'content_id': content_id,
                'worker_id': worker_id
            })
            
            self.logger.debug(f"Content locked by {worker_id}: {content_id}")
            return True
    
    def unlock_content(self, worker_id: str, content_id: str) -> bool:
        """
        Unlock content to allow modifications by others.
        
        Args:
            worker_id: ID of the worker releasing the lock
            content_id: ID of the content to unlock
            
        Returns:
            True if unlock was successful
        """
        with self.content_lock:
            if content_id not in self.content_locks:
                return False
            
            # Check if worker owns the lock
            if self.content_locks[content_id] != worker_id:
                return False
            
            # Release lock
            del self.content_locks[content_id]
            if content_id in self.contents:
                self.contents[content_id].is_locked = False
                self.contents[content_id].locked_by = None
            self.statistics['locked_items'] -= 1
            
            # Notify subscribers
            self._notify_subscribers({
                'type': 'content_unlocked',
                'content_id': content_id,
                'worker_id': worker_id
            })
            
            self.logger.debug(f"Content unlocked by {worker_id}: {content_id}")
            return True
    
    def clear_whiteboard(self, worker_id: str) -> bool:
        """
        Clear all content from the whiteboard.
        
        Args:
            worker_id: ID of the worker clearing the whiteboard
            
        Returns:
            True if clearing was successful
        """
        with self.content_lock:
            # Check for any locked content by other workers
            for content_id, locked_by in self.content_locks.items():
                if locked_by != worker_id:
                    self.logger.warning(f"Cannot clear whiteboard - content {content_id} is locked by {locked_by}")
                    return False
            
            # Clear all content
            old_content_count = len(self.contents)
            self.contents.clear()
            self.content_locks.clear()
            
            # Update statistics
            self.statistics['total_content_items'] = 0
            self.statistics['locked_items'] = 0
            
            # Record change
            change = self._record_change(
                content_id="all",
                operation=ContentOperation.DELETE,
                old_data={'content_count': old_content_count},
                new_data={'content_count': 0},
                changed_by=worker_id,
                description="Cleared entire whiteboard"
            )
            
            # Notify subscribers
            self._notify_subscribers({
                'type': 'whiteboard_cleared',
                'change': self._serialize_change(change),
                'worker_id': worker_id
            })
            
            self.logger.info(f"Whiteboard cleared by {worker_id}")
            return True
    
    def subscribe_to_changes(self, worker_id: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Subscribe to receive real-time change notifications.
        
        Args:
            worker_id: ID of the worker subscribing
            callback: Function to call when changes occur
            
        Returns:
            True if subscription was successful
        """
        with self.subscriber_lock:
            self.subscribers[worker_id] = callback
            self.statistics['active_subscribers'] = len(self.subscribers)
            
            self.logger.debug(f"Worker {worker_id} subscribed to whiteboard changes")
            return True
    
    def unsubscribe_from_changes(self, worker_id: str) -> None:
        """
        Unsubscribe from change notifications.
        
        Args:
            worker_id: ID of the worker unsubscribing
        """
        with self.subscriber_lock:
            if worker_id in self.subscribers:
                del self.subscribers[worker_id]
                self.statistics['active_subscribers'] = len(self.subscribers)
                
                self.logger.debug(f"Worker {worker_id} unsubscribed from whiteboard changes")
    
    def get_change_history(self, limit: Optional[int] = None,
                          since: Optional[datetime] = None,
                          content_id: Optional[str] = None) -> List[ContentChange]:
        """
        Get change history for the whiteboard.
        
        Args:
            limit: Maximum number of changes to return
            since: Only return changes after this timestamp
            content_id: Optional filter by specific content ID
            
        Returns:
            List of ContentChange instances
        """
        with self.change_lock:
            changes = self.change_history.copy()
            
            # Apply filters
            if since:
                changes = [c for c in changes if c.timestamp > since]
            
            if content_id:
                changes = [c for c in changes if c.content_id == content_id]
            
            # Sort by timestamp (newest first)
            changes.sort(key=lambda c: c.timestamp, reverse=True)
            
            # Apply limit
            if limit:
                changes = changes[:limit]
            
            return changes
    
    def get_whiteboard_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the whiteboard.
        
        Returns:
            Dictionary containing whiteboard statistics
        """
        with self.content_lock:
            content_types = {}
            for content in self.contents.values():
                content_type = content.content_type.value
                content_types[content_type] = content_types.get(content_type, 0) + 1
            
            return {
                **self.statistics,
                'whiteboard_id': self.whiteboard_id,
                'space_id': self.space_id,
                'name': self.name,
                'created_at': self.created_at,
                'content_by_type': content_types,
                'total_changes': len(self.change_history)
            }
    
    def export_whiteboard(self, format: str = "json") -> Union[str, Dict[str, Any]]:
        """
        Export whiteboard content in the specified format.
        
        Args:
            format: Export format ("json" or "dict")
            
        Returns:
            Exported whiteboard data
        """
        with self.content_lock:
            export_data = {
                'whiteboard_id': self.whiteboard_id,
                'space_id': self.space_id,
                'name': self.name,
                'created_at': self.created_at.isoformat(),
                'exported_at': datetime.now().isoformat(),
                'contents': [self._serialize_content(content) for content in self.contents.values()],
                'statistics': self.get_whiteboard_statistics()
            }
            
            if format == "json":
                return json.dumps(export_data, indent=2, default=str)
            else:
                return export_data
    
    def _is_content_locked(self, content_id: str, worker_id: str) -> bool:
        """Check if content is locked by another worker."""
        if content_id not in self.content_locks:
            return False
        
        return self.content_locks[content_id] != worker_id
    
    def _record_change(self, content_id: str, operation: ContentOperation,
                      old_data: Optional[Dict[str, Any]], new_data: Optional[Dict[str, Any]],
                      changed_by: str, description: str) -> ContentChange:
        """Record a change in the change history."""
        change = ContentChange(
            change_id=str(uuid.uuid4()),
            content_id=content_id,
            operation=operation,
            old_data=old_data,
            new_data=new_data,
            changed_by=changed_by,
            timestamp=datetime.now(),
            description=description
        )
        
        with self.change_lock:
            self.change_history.append(change)
            self.statistics['total_changes'] += 1
            
            # Keep only last 1000 changes to prevent memory issues
            if len(self.change_history) > 1000:
                self.change_history = self.change_history[-1000:]
        
        return change
    
    def _notify_subscribers(self, notification: Dict[str, Any]) -> None:
        """Notify all subscribers of a change."""
        with self.subscriber_lock:
            for worker_id, callback in self.subscribers.items():
                try:
                    callback(notification)
                except Exception as e:
                    self.logger.error(f"Failed to notify subscriber {worker_id}: {e}")
    
    def _serialize_content(self, content: WhiteboardContent) -> Dict[str, Any]:
        """Serialize content to dictionary format."""
        return {
            'content_id': content.content_id,
            'content_type': content.content_type.value,
            'position': {
                'x': content.position.x,
                'y': content.position.y,
                'z': content.position.z
            },
            'size': {
                'width': content.size.width,
                'height': content.size.height
            },
            'data': content.data,
            'style': content.style,
            'created_by': content.created_by,
            'created_at': content.created_at.isoformat(),
            'last_modified_by': content.last_modified_by,
            'last_modified_at': content.last_modified_at.isoformat(),
            'version': content.version,
            'is_locked': content.is_locked,
            'locked_by': content.locked_by,
            'tags': list(content.tags)
        }
    
    def _serialize_change(self, change: ContentChange) -> Dict[str, Any]:
        """Serialize change to dictionary format."""
        return {
            'change_id': change.change_id,
            'content_id': change.content_id,
            'operation': change.operation.value,
            'old_data': change.old_data,
            'new_data': change.new_data,
            'changed_by': change.changed_by,
            'timestamp': change.timestamp.isoformat(),
            'description': change.description
        }
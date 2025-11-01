"""
Core interfaces and abstract classes for the Botted Library

Defines the contracts and boundaries between system components.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
import uuid
from .exceptions import DataValidationError, SerializationError


class TaskStatus(Enum):
    """Enumeration for task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_CLARIFICATION = "requires_clarification"


class MemoryType(Enum):
    """Enumeration for memory storage types"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class ActionType(Enum):
    """Enumeration for browser action types"""
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    EXTRACT = "extract"


class WorkerType(Enum):
    """Enumeration for collaborative worker types"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


@dataclass
class Task:
    """Data model for task representation"""
    id: str
    description: str
    parameters: Dict[str, Any]
    priority: int
    deadline: Optional[datetime] = None
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}
        self.validate()

    def validate(self) -> None:
        """Validate task data"""
        if not self.id or not isinstance(self.id, str):
            raise DataValidationError("Task ID must be a non-empty string", 
                                    field_name="id", field_value=self.id, model_type="Task")
        
        if not self.description or not isinstance(self.description, str):
            raise DataValidationError("Task description must be a non-empty string",
                                    field_name="description", field_value=self.description, model_type="Task")
        
        if not isinstance(self.parameters, dict):
            raise DataValidationError("Task parameters must be a dictionary",
                                    field_name="parameters", field_value=type(self.parameters).__name__, model_type="Task")
        
        if not isinstance(self.priority, int) or self.priority < 0:
            raise DataValidationError("Task priority must be a non-negative integer",
                                    field_name="priority", field_value=self.priority, model_type="Task")
        
        if self.deadline is not None and not isinstance(self.deadline, datetime):
            raise DataValidationError("Task deadline must be a datetime object or None",
                                    field_name="deadline", field_value=type(self.deadline).__name__, model_type="Task")
        
        if not isinstance(self.context, dict):
            raise DataValidationError("Task context must be a dictionary",
                                    field_name="context", field_value=type(self.context).__name__, model_type="Task")

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        data = asdict(self)
        if self.deadline:
            data['deadline'] = self.deadline.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        if 'deadline' in data and data['deadline']:
            data['deadline'] = datetime.fromisoformat(data['deadline'])
        return cls(**data)

    def to_json(self) -> str:
        """Convert task to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'Task':
        """Create task from JSON string"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise SerializationError("Failed to deserialize Task from JSON",
                                   data_type="Task", operation="from_json", original_exception=e)

    @classmethod
    def create_new(cls, description: str, parameters: Dict[str, Any], 
                   priority: int = 1, deadline: Optional[datetime] = None,
                   context: Optional[Dict[str, Any]] = None) -> 'Task':
        """Create a new task with auto-generated ID"""
        return cls(
            id=str(uuid.uuid4()),
            description=description,
            parameters=parameters,
            priority=priority,
            deadline=deadline,
            context=context or {}
        )


@dataclass
class TaskResult:
    """Data model for task execution results"""
    task_id: str
    status: TaskStatus
    result_data: Dict[str, Any]
    execution_time: float
    confidence_score: float
    sources_used: List[str]

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate task result data"""
        if not self.task_id or not isinstance(self.task_id, str):
            raise DataValidationError("Task ID must be a non-empty string",
                                    field_name="task_id", field_value=self.task_id, model_type="TaskResult")
        
        if not isinstance(self.status, TaskStatus):
            raise DataValidationError("Status must be a TaskStatus enum value",
                                    field_name="status", field_value=type(self.status).__name__, model_type="TaskResult")
        
        if not isinstance(self.result_data, dict):
            raise DataValidationError("Result data must be a dictionary",
                                    field_name="result_data", field_value=type(self.result_data).__name__, model_type="TaskResult")
        
        if not isinstance(self.execution_time, (int, float)) or self.execution_time < 0:
            raise DataValidationError("Execution time must be a non-negative number",
                                    field_name="execution_time", field_value=self.execution_time, model_type="TaskResult")
        
        if not isinstance(self.confidence_score, (int, float)) or not (0 <= self.confidence_score <= 1):
            raise DataValidationError("Confidence score must be a number between 0 and 1",
                                    field_name="confidence_score", field_value=self.confidence_score, model_type="TaskResult")
        
        if not isinstance(self.sources_used, list):
            raise DataValidationError("Sources used must be a list",
                                    field_name="sources_used", field_value=type(self.sources_used).__name__, model_type="TaskResult")
        
        if not all(isinstance(source, str) for source in self.sources_used):
            raise DataValidationError("All sources must be strings",
                                    field_name="sources_used", field_value="mixed types", model_type="TaskResult")

    def to_dict(self) -> Dict[str, Any]:
        """Convert task result to dictionary for serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """Create task result from dictionary"""
        data['status'] = TaskStatus(data['status'])
        return cls(**data)

    def to_json(self) -> str:
        """Convert task result to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'TaskResult':
        """Create task result from JSON string"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise SerializationError("Failed to deserialize TaskResult from JSON",
                                   data_type="TaskResult", operation="from_json", original_exception=e)

    def is_successful(self) -> bool:
        """Check if task execution was successful"""
        return self.status == TaskStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if task execution failed"""
        return self.status == TaskStatus.FAILED


@dataclass
class MemoryEntry:
    """Data model for memory storage entries"""
    id: str
    content: Dict[str, Any]
    timestamp: datetime
    memory_type: MemoryType
    relevance_score: float
    tags: List[str]

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate memory entry data"""
        if not self.id or not isinstance(self.id, str):
            raise DataValidationError("Memory entry ID must be a non-empty string",
                                    field_name="id", field_value=self.id, model_type="MemoryEntry")
        
        if not isinstance(self.content, dict):
            raise DataValidationError("Memory content must be a dictionary",
                                    field_name="content", field_value=type(self.content).__name__, model_type="MemoryEntry")
        
        if not isinstance(self.timestamp, datetime):
            raise DataValidationError("Timestamp must be a datetime object",
                                    field_name="timestamp", field_value=type(self.timestamp).__name__, model_type="MemoryEntry")
        
        if not isinstance(self.memory_type, MemoryType):
            raise DataValidationError("Memory type must be a MemoryType enum value",
                                    field_name="memory_type", field_value=type(self.memory_type).__name__, model_type="MemoryEntry")
        
        if not isinstance(self.relevance_score, (int, float)) or not (0 <= self.relevance_score <= 1):
            raise DataValidationError("Relevance score must be a number between 0 and 1",
                                    field_name="relevance_score", field_value=self.relevance_score, model_type="MemoryEntry")
        
        if not isinstance(self.tags, list):
            raise DataValidationError("Tags must be a list",
                                    field_name="tags", field_value=type(self.tags).__name__, model_type="MemoryEntry")
        
        if not all(isinstance(tag, str) for tag in self.tags):
            raise DataValidationError("All tags must be strings",
                                    field_name="tags", field_value="mixed types", model_type="MemoryEntry")

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory entry to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['memory_type'] = self.memory_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create memory entry from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['memory_type'] = MemoryType(data['memory_type'])
        return cls(**data)

    def to_json(self) -> str:
        """Convert memory entry to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'MemoryEntry':
        """Create memory entry from JSON string"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise SerializationError("Failed to deserialize MemoryEntry from JSON",
                                   data_type="MemoryEntry", operation="from_json", original_exception=e)

    @classmethod
    def create_new(cls, content: Dict[str, Any], memory_type: MemoryType,
                   relevance_score: float = 0.5, tags: Optional[List[str]] = None) -> 'MemoryEntry':
        """Create a new memory entry with auto-generated ID and current timestamp"""
        return cls(
            id=str(uuid.uuid4()),
            content=content,
            timestamp=datetime.now(),
            memory_type=memory_type,
            relevance_score=relevance_score,
            tags=tags or []
        )

    def add_tag(self, tag: str) -> None:
        """Add a tag to the memory entry"""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the memory entry"""
        if tag in self.tags:
            self.tags.remove(tag)


@dataclass
class BrowserAction:
    """Data model for browser actions"""
    action_type: ActionType
    target: str
    parameters: Dict[str, Any]
    expected_outcome: str

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate browser action data"""
        if not isinstance(self.action_type, ActionType):
            raise DataValidationError("Action type must be an ActionType enum value",
                                    field_name="action_type", field_value=type(self.action_type).__name__, model_type="BrowserAction")
        
        if not self.target or not isinstance(self.target, str):
            raise DataValidationError("Target must be a non-empty string",
                                    field_name="target", field_value=self.target, model_type="BrowserAction")
        
        if not isinstance(self.parameters, dict):
            raise DataValidationError("Parameters must be a dictionary",
                                    field_name="parameters", field_value=type(self.parameters).__name__, model_type="BrowserAction")
        
        if not isinstance(self.expected_outcome, str):
            raise DataValidationError("Expected outcome must be a string",
                                    field_name="expected_outcome", field_value=type(self.expected_outcome).__name__, model_type="BrowserAction")
        
        # Validate action-specific parameters
        if self.action_type == ActionType.CLICK:
            # Click actions should have selector or coordinates
            if 'selector' not in self.parameters and 'coordinates' not in self.parameters:
                raise DataValidationError("Click action must have either 'selector' or 'coordinates' parameter",
                                        field_name="parameters", field_value=list(self.parameters.keys()), model_type="BrowserAction")
        
        elif self.action_type == ActionType.TYPE:
            # Type actions should have text to type
            if 'text' not in self.parameters:
                raise DataValidationError("Type action must have 'text' parameter",
                                        field_name="parameters", field_value=list(self.parameters.keys()), model_type="BrowserAction")
        
        elif self.action_type == ActionType.SCROLL:
            # Scroll actions should have direction and amount
            if 'direction' not in self.parameters:
                raise DataValidationError("Scroll action must have 'direction' parameter",
                                        field_name="parameters", field_value=list(self.parameters.keys()), model_type="BrowserAction")
        
        elif self.action_type == ActionType.WAIT:
            # Wait actions should have timeout
            if 'timeout' not in self.parameters:
                raise DataValidationError("Wait action must have 'timeout' parameter",
                                        field_name="parameters", field_value=list(self.parameters.keys()), model_type="BrowserAction")

    def to_dict(self) -> Dict[str, Any]:
        """Convert browser action to dictionary for serialization"""
        data = asdict(self)
        data['action_type'] = self.action_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrowserAction':
        """Create browser action from dictionary"""
        data['action_type'] = ActionType(data['action_type'])
        return cls(**data)

    def to_json(self) -> str:
        """Convert browser action to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'BrowserAction':
        """Create browser action from JSON string"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise SerializationError("Failed to deserialize BrowserAction from JSON",
                                   data_type="BrowserAction", operation="from_json", original_exception=e)

    @classmethod
    def create_click(cls, target: str, selector: str = None, coordinates: tuple = None,
                     expected_outcome: str = "Element clicked") -> 'BrowserAction':
        """Create a click action"""
        parameters = {}
        if selector:
            parameters['selector'] = selector
        if coordinates:
            parameters['coordinates'] = coordinates
        
        return cls(
            action_type=ActionType.CLICK,
            target=target,
            parameters=parameters,
            expected_outcome=expected_outcome
        )

    @classmethod
    def create_type(cls, target: str, text: str, 
                    expected_outcome: str = "Text entered") -> 'BrowserAction':
        """Create a type action"""
        return cls(
            action_type=ActionType.TYPE,
            target=target,
            parameters={'text': text},
            expected_outcome=expected_outcome
        )

    @classmethod
    def create_scroll(cls, target: str, direction: str, amount: int = 1,
                      expected_outcome: str = "Page scrolled") -> 'BrowserAction':
        """Create a scroll action"""
        return cls(
            action_type=ActionType.SCROLL,
            target=target,
            parameters={'direction': direction, 'amount': amount},
            expected_outcome=expected_outcome
        )

    @classmethod
    def create_wait(cls, target: str, timeout: int = 10,
                    expected_outcome: str = "Element appeared") -> 'BrowserAction':
        """Create a wait action"""
        return cls(
            action_type=ActionType.WAIT,
            target=target,
            parameters={'timeout': timeout},
            expected_outcome=expected_outcome
        )


class IMemorySystem(ABC):
    """Interface for memory system implementations"""
    
    @abstractmethod
    def store_short_term(self, data: Dict[str, Any]) -> None:
        """Store data in short-term memory"""
        pass
    
    @abstractmethod
    def store_long_term(self, data: Dict[str, Any]) -> None:
        """Store data in long-term memory"""
        pass
    
    @abstractmethod
    def retrieve_by_query(self, query: str, memory_type: str = "both") -> List[Dict]:
        """Retrieve memory entries by query"""
        pass
    
    @abstractmethod
    def clear_short_term(self) -> None:
        """Clear short-term memory"""
        pass
    
    @abstractmethod
    def get_context(self, task_context: str) -> Dict[str, Any]:
        """Get contextual memory for a task"""
        pass


class IKnowledgeValidator(ABC):
    """Interface for knowledge validation implementations"""
    
    @abstractmethod
    def validate_source(self, source: str) -> float:
        """Validate source reliability, returns reliability score"""
        pass
    
    @abstractmethod
    def check_accuracy(self, data: str, context: str) -> float:
        """Check data accuracy, returns accuracy score"""
        pass
    
    @abstractmethod
    def cross_reference(self, information: str) -> List[Dict[str, Any]]:
        """Cross-reference information against known sources"""
        pass
    
    @abstractmethod
    def update_source_reliability(self, source: str, reliability: float) -> None:
        """Update source reliability based on validation results"""
        pass


class IBrowserController(ABC):
    """Interface for browser controller implementations"""
    
    @abstractmethod
    def open_browser(self, url: str) -> bool:
        """Open browser and navigate to URL"""
        pass
    
    @abstractmethod
    def perform_action(self, action: BrowserAction) -> Dict[str, Any]:
        """Perform a browser action"""
        pass
    
    @abstractmethod
    def close_browser(self) -> None:
        """Close browser session"""
        pass
    
    @abstractmethod
    def get_page_content(self) -> str:
        """Get current page content"""
        pass
    
    @abstractmethod
    def take_screenshot(self) -> bytes:
        """Take screenshot of current page"""
        pass


class ITaskExecutor(ABC):
    """Interface for task executor implementations"""
    
    @abstractmethod
    def process_task(self, task: Task) -> List[BrowserAction]:
        """Process task and return list of browser actions"""
        pass
    
    @abstractmethod
    def validate_task(self, task: Task) -> bool:
        """Validate if task is feasible"""
        pass
    
    @abstractmethod
    def execute_browser_actions(self, actions: List[BrowserAction]) -> TaskResult:
        """Execute browser actions and return result"""
        pass
    
    @abstractmethod
    def monitor_execution(self, task_id: str) -> Dict[str, Any]:
        """Monitor task execution status"""
        pass


class IWorker(ABC):
    """Interface for worker implementations"""
    
    @abstractmethod
    def initialize_role(self, role: str) -> None:
        """Initialize worker with specific role"""
        pass
    
    @abstractmethod
    def execute_task(self, task: Task) -> TaskResult:
        """Execute a task and return result"""
        pass
    
    @abstractmethod
    def update_memory(self, data: Dict[str, Any]) -> None:
        """Update worker memory with new data"""
        pass
    
    @abstractmethod
    def retrieve_memory(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve memory entries by query"""
        pass
    
    @abstractmethod
    def ask_for_clarity(self, query: str) -> str:
        """Request clarification from user"""
        pass
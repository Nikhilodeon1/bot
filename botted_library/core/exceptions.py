"""
Custom exception hierarchy for the Botted Library

Provides specific error types for different system components.
"""

import traceback
from typing import Dict, Any, Optional
from datetime import datetime


class BottedLibraryError(Exception):
    """Base exception for all library errors"""
    
    def __init__(self, message: str, context: Dict[str, Any] = None, 
                 original_exception: Exception = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()
        self.traceback_info = traceback.format_exc() if original_exception else None
    
    def __str__(self):
        error_parts = [self.message]
        
        if self.context:
            error_parts.append(f"Context: {self.context}")
        
        if self.original_exception:
            error_parts.append(f"Original: {str(self.original_exception)}")
        
        if self.timestamp:
            error_parts.append(f"Time: {self.timestamp.isoformat()}")
        
        return " | ".join(error_parts)
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get comprehensive debugging information"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'original_exception': str(self.original_exception) if self.original_exception else None,
            'traceback': self.traceback_info
        }
    
    def add_context(self, key: str, value: Any) -> None:
        """Add additional context information"""
        self.context[key] = value


class WorkerError(BottedLibraryError):
    """Worker-related errors"""
    
    def __init__(self, message: str, worker_id: str = None, role: str = None, 
                 context: Dict[str, Any] = None, original_exception: Exception = None):
        context = context or {}
        if worker_id:
            context['worker_id'] = worker_id
        if role:
            context['role'] = role
        super().__init__(message, context, original_exception)


class TaskExecutionError(BottedLibraryError):
    """Task execution failures"""
    
    def __init__(self, message: str, task_id: str = None, step: str = None,
                 context: Dict[str, Any] = None, original_exception: Exception = None):
        context = context or {}
        if task_id:
            context['task_id'] = task_id
        if step:
            context['execution_step'] = step
        super().__init__(message, context, original_exception)


class BrowserError(BottedLibraryError):
    """Browser interaction errors"""
    
    def __init__(self, message: str, action_type: str = None, target: str = None,
                 browser_state: str = None, context: Dict[str, Any] = None, 
                 original_exception: Exception = None):
        context = context or {}
        if action_type:
            context['action_type'] = action_type
        if target:
            context['target'] = target
        if browser_state:
            context['browser_state'] = browser_state
        super().__init__(message, context, original_exception)


class MemoryError(BottedLibraryError):
    """Memory system errors"""
    
    def __init__(self, message: str, memory_type: str = None, operation: str = None,
                 context: Dict[str, Any] = None, original_exception: Exception = None):
        context = context or {}
        if memory_type:
            context['memory_type'] = memory_type
        if operation:
            context['operation'] = operation
        super().__init__(message, context, original_exception)


class ValidationError(BottedLibraryError):
    """Knowledge validation errors"""
    
    def __init__(self, message: str, source: str = None, validation_type: str = None,
                 confidence_score: float = None, context: Dict[str, Any] = None, 
                 original_exception: Exception = None):
        context = context or {}
        if source:
            context['source'] = source
        if validation_type:
            context['validation_type'] = validation_type
        if confidence_score is not None:
            context['confidence_score'] = confidence_score
        super().__init__(message, context, original_exception)


class RoleError(BottedLibraryError):
    """Role-related errors"""
    
    def __init__(self, message: str, role_name: str = None, capability: str = None,
                 context: Dict[str, Any] = None, original_exception: Exception = None):
        context = context or {}
        if role_name:
            context['role_name'] = role_name
        if capability:
            context['capability'] = capability
        super().__init__(message, context, original_exception)


class ConfigurationError(BottedLibraryError):
    """Configuration and setup errors"""
    
    def __init__(self, message: str, config_key: str = None, config_value: Any = None,
                 context: Dict[str, Any] = None, original_exception: Exception = None):
        context = context or {}
        if config_key:
            context['config_key'] = config_key
        if config_value is not None:
            context['config_value'] = str(config_value)
        super().__init__(message, context, original_exception)


class DataValidationError(BottedLibraryError):
    """Data model validation errors"""
    
    def __init__(self, message: str, field_name: str = None, field_value: Any = None,
                 model_type: str = None, context: Dict[str, Any] = None, 
                 original_exception: Exception = None):
        context = context or {}
        if field_name:
            context['field_name'] = field_name
        if field_value is not None:
            context['field_value'] = str(field_value)
        if model_type:
            context['model_type'] = model_type
        super().__init__(message, context, original_exception)


class SerializationError(BottedLibraryError):
    """Serialization and deserialization errors"""
    
    def __init__(self, message: str, data_type: str = None, operation: str = None,
                 context: Dict[str, Any] = None, original_exception: Exception = None):
        context = context or {}
        if data_type:
            context['data_type'] = data_type
        if operation:
            context['operation'] = operation
        super().__init__(message, context, original_exception)
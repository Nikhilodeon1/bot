"""
Centralized Error Handling and Propagation System

Provides comprehensive error handling, logging, and recovery mechanisms
across all Botted Library components.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum

from .exceptions import (
    BottedLibraryError, WorkerError, TaskExecutionError, BrowserError,
    MemoryError, ValidationError, RoleError, ConfigurationError
)
from ..utils.logger import setup_logger


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    VALIDATION = "validation"
    EXECUTION = "execution"
    NETWORK = "network"
    RESOURCE = "resource"
    USER_INPUT = "user_input"
    SYSTEM = "system"


class ErrorHandler:
    """
    Centralized error handler for the Botted Library.
    
    Provides error classification, logging, recovery strategies,
    and error propagation across all system components.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the error handler.
        
        Args:
            config: Optional configuration for error handling
        """
        self.config = config or {}
        self.logger = setup_logger(__name__)
        
        # Error tracking
        self.error_history: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}
        self.recovery_strategies: Dict[str, Callable] = {}
        
        # Configuration
        self.max_error_history = self.config.get('max_error_history', 1000)
        self.enable_auto_recovery = self.config.get('enable_auto_recovery', True)
        self.log_all_errors = self.config.get('log_all_errors', True)
        
        # Register default recovery strategies
        self._register_default_recovery_strategies()
        
        self.logger.info("Error handler initialized")
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None,
                    component: str = None, operation: str = None) -> Dict[str, Any]:
        """
        Handle an error with comprehensive processing.
        
        Args:
            error: The exception to handle
            context: Additional context information
            component: Component where error occurred
            operation: Operation being performed when error occurred
            
        Returns:
            Dict containing error handling results and recommendations
        """
        try:
            # Create comprehensive error record
            error_record = self._create_error_record(error, context, component, operation)
            
            # Classify error
            classification = self._classify_error(error, error_record)
            error_record.update(classification)
            
            # Log error appropriately
            if self.log_all_errors:
                self._log_error(error_record)
            
            # Track error statistics
            self._track_error_statistics(error_record)
            
            # Store in error history
            self._store_error_history(error_record)
            
            # Determine recovery strategy
            recovery_result = self._attempt_recovery(error, error_record)
            error_record['recovery_result'] = recovery_result
            
            # Generate recommendations
            recommendations = self._generate_recommendations(error_record)
            error_record['recommendations'] = recommendations
            
            return {
                'error_id': error_record['error_id'],
                'severity': error_record['severity'],
                'category': error_record['category'],
                'recoverable': recovery_result.get('success', False),
                'recovery_action': recovery_result.get('action'),
                'recommendations': recommendations,
                'should_retry': recovery_result.get('should_retry', False),
                'should_escalate': error_record['severity'] in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
            }
            
        except Exception as handler_error:
            # Error in error handler - log and return minimal response
            self.logger.critical(f"Error handler failed: {str(handler_error)}")
            return {
                'error_id': 'handler_failure',
                'severity': ErrorSeverity.CRITICAL,
                'category': ErrorCategory.SYSTEM,
                'recoverable': False,
                'recommendations': ['Contact system administrator'],
                'should_retry': False,
                'should_escalate': True
            }
    
    def _create_error_record(self, error: Exception, context: Dict[str, Any] = None,
                           component: str = None, operation: str = None) -> Dict[str, Any]:
        """Create comprehensive error record."""
        error_id = f"err_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(error)}"
        
        # Extract error information
        error_info = {
            'error_id': error_id,
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'component': component,
            'operation': operation,
            'context': context or {},
            'traceback': traceback.format_exc()
        }
        
        # Add Botted Library specific error information
        if isinstance(error, BottedLibraryError):
            error_info.update({
                'library_error': True,
                'error_context': error.context,
                'original_exception': str(error.original_exception) if error.original_exception else None,
                'debug_info': error.get_debug_info()
            })
        else:
            error_info['library_error'] = False
        
        return error_info
    
    def _classify_error(self, error: Exception, error_record: Dict[str, Any]) -> Dict[str, str]:
        """Classify error by severity and category."""
        # Determine severity
        severity = self._determine_severity(error, error_record)
        
        # Determine category
        category = self._determine_category(error, error_record)
        
        return {
            'severity': severity,
            'category': category
        }
    
    def _determine_severity(self, error: Exception, error_record: Dict[str, Any]) -> ErrorSeverity:
        """Determine error severity level."""
        error_type = type(error).__name__
        
        # Critical errors
        if isinstance(error, (SystemError, MemoryError, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if isinstance(error, (ConfigurationError, ImportError)):
            return ErrorSeverity.HIGH
        
        if 'database' in str(error).lower() or 'connection' in str(error).lower():
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if isinstance(error, (WorkerError, TaskExecutionError, BrowserError)):
            return ErrorSeverity.MEDIUM
        
        if isinstance(error, (ValidationError, RoleError)):
            return ErrorSeverity.MEDIUM
        
        # Low severity errors (default)
        return ErrorSeverity.LOW
    
    def _determine_category(self, error: Exception, error_record: Dict[str, Any]) -> ErrorCategory:
        """Determine error category."""
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # Configuration errors
        if isinstance(error, ConfigurationError) or 'config' in error_message:
            return ErrorCategory.CONFIGURATION
        
        # Dependency errors
        if isinstance(error, ImportError) or 'import' in error_message:
            return ErrorCategory.DEPENDENCY
        
        # Validation errors
        if isinstance(error, ValidationError) or 'validation' in error_message:
            return ErrorCategory.VALIDATION
        
        # Execution errors
        if isinstance(error, (TaskExecutionError, WorkerError)):
            return ErrorCategory.EXECUTION
        
        # Network errors
        if any(term in error_message for term in ['network', 'connection', 'timeout', 'http']):
            return ErrorCategory.NETWORK
        
        # Resource errors
        if any(term in error_message for term in ['memory', 'disk', 'file', 'resource']):
            return ErrorCategory.RESOURCE
        
        # Browser errors
        if isinstance(error, BrowserError):
            return ErrorCategory.EXECUTION
        
        # Default to system
        return ErrorCategory.SYSTEM
    
    def _log_error(self, error_record: Dict[str, Any]) -> None:
        """Log error with appropriate level."""
        severity = error_record.get('severity', ErrorSeverity.LOW)
        error_id = error_record.get('error_id', 'unknown')
        error_message = error_record.get('error_message', 'Unknown error')
        component = error_record.get('component', 'unknown')
        
        log_message = f"[{error_id}] {component}: {error_message}"
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Log additional context for higher severity errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            if error_record.get('context'):
                self.logger.error(f"[{error_id}] Context: {error_record['context']}")
            if error_record.get('traceback'):
                self.logger.error(f"[{error_id}] Traceback: {error_record['traceback']}")
    
    def _track_error_statistics(self, error_record: Dict[str, Any]) -> None:
        """Track error statistics for monitoring."""
        error_type = error_record.get('error_type', 'unknown')
        component = error_record.get('component', 'unknown')
        
        # Count by error type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Count by component
        component_key = f"component_{component}"
        self.error_counts[component_key] = self.error_counts.get(component_key, 0) + 1
        
        # Count by severity
        severity = error_record.get('severity', ErrorSeverity.LOW)
        severity_key = f"severity_{severity.value}"
        self.error_counts[severity_key] = self.error_counts.get(severity_key, 0) + 1
    
    def _store_error_history(self, error_record: Dict[str, Any]) -> None:
        """Store error in history with size management."""
        self.error_history.append(error_record)
        
        # Maintain history size limit
        if len(self.error_history) > self.max_error_history:
            # Remove oldest errors, keeping critical ones
            critical_errors = [e for e in self.error_history if e.get('severity') == ErrorSeverity.CRITICAL]
            recent_errors = self.error_history[-(self.max_error_history - len(critical_errors)):]
            self.error_history = critical_errors + recent_errors
    
    def _attempt_recovery(self, error: Exception, error_record: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt automatic error recovery."""
        if not self.enable_auto_recovery:
            return {'success': False, 'action': 'auto_recovery_disabled'}
        
        error_type = type(error).__name__
        category = error_record.get('category')
        
        # Try specific recovery strategy
        if error_type in self.recovery_strategies:
            try:
                recovery_result = self.recovery_strategies[error_type](error, error_record)
                return recovery_result
            except Exception as recovery_error:
                self.logger.warning(f"Recovery strategy failed: {str(recovery_error)}")
        
        # Try category-based recovery
        if category and category.value in self.recovery_strategies:
            try:
                recovery_result = self.recovery_strategies[category.value](error, error_record)
                return recovery_result
            except Exception as recovery_error:
                self.logger.warning(f"Category recovery failed: {str(recovery_error)}")
        
        # Default recovery attempt
        return self._default_recovery(error, error_record)
    
    def _default_recovery(self, error: Exception, error_record: Dict[str, Any]) -> Dict[str, Any]:
        """Default recovery strategy."""
        severity = error_record.get('severity', ErrorSeverity.LOW)
        
        if severity == ErrorSeverity.LOW:
            return {
                'success': True,
                'action': 'continue_with_warning',
                'should_retry': False
            }
        elif severity == ErrorSeverity.MEDIUM:
            return {
                'success': False,
                'action': 'retry_recommended',
                'should_retry': True
            }
        else:
            return {
                'success': False,
                'action': 'manual_intervention_required',
                'should_retry': False
            }
    
    def _generate_recommendations(self, error_record: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on error analysis."""
        recommendations = []
        
        error_type = error_record.get('error_type', '')
        category = error_record.get('category')
        severity = error_record.get('severity')
        
        # Category-based recommendations
        if category == ErrorCategory.CONFIGURATION:
            recommendations.extend([
                "Check configuration file syntax and values",
                "Verify all required configuration keys are present",
                "Ensure file paths and URLs are accessible"
            ])
        elif category == ErrorCategory.DEPENDENCY:
            recommendations.extend([
                "Check if all required packages are installed",
                "Verify package versions are compatible",
                "Run 'pip install -r requirements.txt'"
            ])
        elif category == ErrorCategory.NETWORK:
            recommendations.extend([
                "Check internet connectivity",
                "Verify firewall and proxy settings",
                "Retry the operation after a brief delay"
            ])
        elif category == ErrorCategory.RESOURCE:
            recommendations.extend([
                "Check available disk space and memory",
                "Close unnecessary applications",
                "Consider increasing system resources"
            ])
        
        # Severity-based recommendations
        if severity == ErrorSeverity.CRITICAL:
            recommendations.extend([
                "Stop all operations and investigate immediately",
                "Check system logs for additional information",
                "Contact system administrator if needed"
            ])
        elif severity == ErrorSeverity.HIGH:
            recommendations.extend([
                "Review error details and context carefully",
                "Consider restarting the affected component",
                "Check for recent configuration changes"
            ])
        
        # Error type specific recommendations
        if 'timeout' in error_type.lower():
            recommendations.append("Increase timeout values in configuration")
        
        if 'permission' in str(error_record.get('error_message', '')).lower():
            recommendations.append("Check file and directory permissions")
        
        return recommendations[:5]  # Limit to 5 most relevant recommendations
    
    def _register_default_recovery_strategies(self) -> None:
        """Register default recovery strategies."""
        
        def network_recovery(error: Exception, error_record: Dict[str, Any]) -> Dict[str, Any]:
            """Recovery strategy for network errors."""
            return {
                'success': True,
                'action': 'retry_with_backoff',
                'should_retry': True,
                'retry_delay': 5.0
            }
        
        def resource_recovery(error: Exception, error_record: Dict[str, Any]) -> Dict[str, Any]:
            """Recovery strategy for resource errors."""
            return {
                'success': False,
                'action': 'cleanup_and_retry',
                'should_retry': True,
                'cleanup_required': True
            }
        
        def validation_recovery(error: Exception, error_record: Dict[str, Any]) -> Dict[str, Any]:
            """Recovery strategy for validation errors."""
            return {
                'success': False,
                'action': 'request_user_input',
                'should_retry': False,
                'user_intervention_required': True
            }
        
        # Register strategies
        self.recovery_strategies.update({
            ErrorCategory.NETWORK.value: network_recovery,
            ErrorCategory.RESOURCE.value: resource_recovery,
            ErrorCategory.VALIDATION.value: validation_recovery
        })
    
    def register_recovery_strategy(self, error_type: str, strategy: Callable) -> None:
        """Register a custom recovery strategy."""
        self.recovery_strategies[error_type] = strategy
        self.logger.info(f"Registered recovery strategy for: {error_type}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and analysis."""
        total_errors = len(self.error_history)
        
        if total_errors == 0:
            return {'total_errors': 0, 'message': 'No errors recorded'}
        
        # Calculate statistics
        recent_errors = [e for e in self.error_history if 
                        (datetime.now() - datetime.fromisoformat(e['timestamp'])).total_seconds() < 3600]
        
        severity_counts = {}
        category_counts = {}
        component_counts = {}
        
        for error in self.error_history:
            severity = error.get('severity', 'unknown')
            category = error.get('category', 'unknown')
            component = error.get('component', 'unknown')
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
            component_counts[component] = component_counts.get(component, 0) + 1
        
        return {
            'total_errors': total_errors,
            'recent_errors_1h': len(recent_errors),
            'severity_distribution': severity_counts,
            'category_distribution': category_counts,
            'component_distribution': component_counts,
            'most_common_error': max(self.error_counts.items(), key=lambda x: x[1]) if self.error_counts else None,
            'error_rate_per_hour': len(recent_errors)
        }
    
    def clear_error_history(self) -> None:
        """Clear error history (useful for testing)."""
        self.error_history.clear()
        self.error_counts.clear()
        self.logger.info("Error history cleared")


# Global error handler instance
_default_error_handler = None


def get_default_error_handler() -> ErrorHandler:
    """Get or create the default error handler."""
    global _default_error_handler
    if _default_error_handler is None:
        _default_error_handler = ErrorHandler()
    return _default_error_handler


def handle_error(error: Exception, context: Dict[str, Any] = None,
                component: str = None, operation: str = None) -> Dict[str, Any]:
    """Handle an error using the default error handler."""
    handler = get_default_error_handler()
    return handler.handle_error(error, context, component, operation)
"""
Logging utilities for the Botted Library

Provides centralized logging configuration with support for file and console output,
log rotation, and different log levels for different components.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            )
        
        return super().format(record)


class BottedLibraryLogger:
    """
    Centralized logger manager for the Botted Library
    
    Handles logger configuration, file rotation, and provides
    consistent logging across all components.
    """
    
    def __init__(self):
        self._loggers: Dict[str, logging.Logger] = {}
        self._configured = False
        self._config: Dict[str, Any] = {}
    
    def configure(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Configure logging system with provided configuration
        
        Args:
            config: Logging configuration dictionary
        """
        if self._configured:
            return
        
        # Default configuration
        default_config = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file_path': None,
            'max_file_size': 10485760,  # 10MB
            'backup_count': 5,
            'console_output': True,
            'colored_output': True
        }
        
        # Merge with provided config
        self._config = {**default_config, **(config or {})}
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self._config['level'].upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add console handler if enabled
        if self._config['console_output']:
            console_handler = logging.StreamHandler(sys.stdout)
            
            if self._config['colored_output']:
                console_formatter = ColoredFormatter(self._config['format'])
            else:
                console_formatter = logging.Formatter(self._config['format'])
            
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(getattr(logging, self._config['level'].upper()))
            root_logger.addHandler(console_handler)
        
        # Add file handler if file path specified
        if self._config['file_path']:
            self._setup_file_handler(root_logger)
        
        self._configured = True
    
    def _setup_file_handler(self, logger: logging.Logger) -> None:
        """Set up rotating file handler"""
        try:
            log_path = Path(self._config['file_path'])
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_path,
                maxBytes=self._config['max_file_size'],
                backupCount=self._config['backup_count'],
                encoding='utf-8'
            )
            
            file_formatter = logging.Formatter(self._config['format'])
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(getattr(logging, self._config['level'].upper()))
            
            logger.addHandler(file_handler)
            
        except Exception as e:
            # Fallback to console logging if file setup fails
            print(f"Warning: Failed to setup file logging: {str(e)}")
    
    def get_logger(self, name: str, level: Optional[str] = None) -> logging.Logger:
        """
        Get or create logger instance
        
        Args:
            name: Logger name (typically module name)
            level: Optional specific log level for this logger
            
        Returns:
            Configured logger instance
        """
        if not self._configured:
            self.configure()
        
        if name not in self._loggers:
            logger = logging.getLogger(name)
            
            # Set specific level if provided
            if level:
                logger.setLevel(getattr(logging, level.upper()))
            
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def set_level(self, name: str, level: str) -> None:
        """
        Set log level for specific logger
        
        Args:
            name: Logger name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if name in self._loggers:
            self._loggers[name].setLevel(getattr(logging, level.upper()))
        else:
            # Create logger with specific level
            self.get_logger(name, level)
    
    def add_file_handler(self, name: str, file_path: str, 
                        level: str = 'INFO', format_str: Optional[str] = None) -> None:
        """
        Add file handler to specific logger
        
        Args:
            name: Logger name
            file_path: Path to log file
            level: Log level for file handler
            format_str: Optional custom format string
        """
        logger = self.get_logger(name)
        
        try:
            log_path = Path(file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_path,
                maxBytes=self._config['max_file_size'],
                backupCount=self._config['backup_count'],
                encoding='utf-8'
            )
            
            formatter = logging.Formatter(format_str or self._config['format'])
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, level.upper()))
            
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.warning(f"Failed to add file handler for {name}: {str(e)}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current logging configuration"""
        return self._config.copy()
    
    def shutdown(self) -> None:
        """Shutdown logging system"""
        logging.shutdown()
        self._configured = False
        self._loggers.clear()


# Global logger manager instance
_logger_manager = BottedLibraryLogger()


def setup_logger(name: str, level: str = "INFO", log_file: Optional[str] = None, 
                config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Set up logger for the application
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        config: Optional logging configuration
        
    Returns:
        Configured logger instance
    """
    global _logger_manager
    
    # Configure logger manager if config provided
    if config:
        _logger_manager.configure(config)
    elif not _logger_manager._configured:
        # Use default configuration with optional file
        default_config = {}
        if log_file:
            default_config['file_path'] = log_file
        _logger_manager.configure(default_config)
    
    # Get logger with specific level
    logger = _logger_manager.get_logger(name, level)
    
    # Add specific file handler if requested
    if log_file and log_file != _logger_manager._config.get('file_path'):
        _logger_manager.add_file_handler(name, log_file, level)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance by name
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    global _logger_manager
    return _logger_manager.get_logger(name)


def configure_logging(config: Dict[str, Any]) -> None:
    """
    Configure global logging settings
    
    Args:
        config: Logging configuration dictionary
    """
    global _logger_manager
    _logger_manager.configure(config)


def set_log_level(name: str, level: str) -> None:
    """
    Set log level for specific logger
    
    Args:
        name: Logger name
        level: Log level
    """
    global _logger_manager
    _logger_manager.set_level(name, level)


def add_file_handler(name: str, file_path: str, level: str = 'INFO') -> None:
    """
    Add file handler to specific logger
    
    Args:
        name: Logger name
        file_path: Path to log file
        level: Log level for file handler
    """
    global _logger_manager
    _logger_manager.add_file_handler(name, file_path, level)


def get_logging_config() -> Dict[str, Any]:
    """Get current logging configuration"""
    global _logger_manager
    return _logger_manager.get_config()


def shutdown_logging() -> None:
    """Shutdown logging system"""
    global _logger_manager
    _logger_manager.shutdown()


# Convenience functions for common logging patterns
def log_function_call(logger: logging.Logger, func_name: str, args: tuple = (), 
                     kwargs: Dict[str, Any] = None) -> None:
    """
    Log function call with arguments
    
    Args:
        logger: Logger instance
        func_name: Function name
        args: Function arguments
        kwargs: Function keyword arguments
    """
    kwargs = kwargs or {}
    logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")


def log_execution_time(logger: logging.Logger, func_name: str, 
                      start_time: datetime, end_time: datetime) -> None:
    """
    Log function execution time
    
    Args:
        logger: Logger instance
        func_name: Function name
        start_time: Start timestamp
        end_time: End timestamp
    """
    execution_time = (end_time - start_time).total_seconds()
    logger.info(f"{func_name} completed in {execution_time:.3f} seconds")


def log_error_with_context(logger: logging.Logger, error: Exception, 
                          context: Dict[str, Any] = None) -> None:
    """
    Log error with additional context
    
    Args:
        logger: Logger instance
        error: Exception instance
        context: Additional context information
    """
    context = context or {}
    logger.error(f"Error: {str(error)} | Type: {type(error).__name__} | Context: {context}")


def create_component_logger(component_name: str, level: str = 'INFO', 
                          log_file: Optional[str] = None) -> logging.Logger:
    """
    Create logger for specific component with consistent naming
    
    Args:
        component_name: Component name (e.g., 'worker', 'memory', 'browser')
        level: Log level
        log_file: Optional component-specific log file
        
    Returns:
        Configured logger for component
    """
    logger_name = f"botted_library.{component_name}"
    return setup_logger(logger_name, level, log_file)
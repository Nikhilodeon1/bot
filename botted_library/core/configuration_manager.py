"""
Configuration Management System for Botted Library v2

Provides comprehensive configuration management with validation, 
environment-specific settings, and dynamic updates.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
from datetime import datetime

from .interfaces import WorkerType


class ConfigurationSource(Enum):
    """Configuration source types"""
    DEFAULT = "default"
    FILE = "file"
    ENVIRONMENT = "environment"
    RUNTIME = "runtime"


class ConfigurationError(Exception):
    """Configuration-related errors"""
    pass


@dataclass
class ValidationRule:
    """Configuration validation rule"""
    field_path: str
    validator: Callable[[Any], bool]
    error_message: str
    required: bool = True


@dataclass
class ConfigurationSchema:
    """Configuration schema definition"""
    # Server configuration
    server_host: str = "localhost"
    server_port: int = 8765
    server_max_connections: int = 100
    server_timeout: int = 30
    server_ssl_enabled: bool = False
    server_ssl_cert_path: Optional[str] = None
    server_ssl_key_path: Optional[str] = None
    
    # Worker configuration
    max_workers_per_type: Dict[str, int] = field(default_factory=lambda: {
        "PLANNER": 5,
        "EXECUTOR": 20,
        "VERIFIER": 10
    })
    worker_timeout: int = 300
    worker_heartbeat_interval: int = 60
    worker_max_memory_mb: int = 1024
    worker_max_cpu_percent: float = 80.0
    
    # Collaborative spaces configuration
    max_collaborative_spaces: int = 50
    max_participants_per_space: int = 20
    space_timeout: int = 3600  # 1 hour
    space_cleanup_interval: int = 300  # 5 minutes
    
    # Plugin system configuration
    plugin_directories: List[str] = field(default_factory=lambda: [
        "plugins", 
        "~/.botted_library/plugins",
        "/usr/local/lib/botted_library/plugins"
    ])
    auto_load_plugins: bool = True
    plugin_timeout: int = 60
    max_plugins: int = 100
    
    # Enhanced tools configuration
    tool_timeout: int = 300
    max_concurrent_tools: int = 10
    tool_retry_attempts: int = 3
    tool_cache_enabled: bool = True
    tool_cache_size_mb: int = 256
    
    # Monitoring configuration
    enable_monitoring: bool = True
    monitoring_interval: int = 30
    metrics_retention_days: int = 7
    performance_alerts_enabled: bool = True
    performance_threshold_cpu: float = 90.0
    performance_threshold_memory: float = 85.0
    
    # Logging configuration
    log_level: str = "INFO"
    log_file_path: Optional[str] = None
    log_max_size_mb: int = 100
    log_backup_count: int = 5
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Error recovery configuration
    enable_error_recovery: bool = True
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_exponential_backoff: bool = True
    error_notification_enabled: bool = False
    error_notification_email: Optional[str] = None
    
    # Performance configuration
    message_queue_size: int = 1000
    message_batch_size: int = 10
    cleanup_interval: int = 300
    gc_interval: int = 600  # 10 minutes
    
    # Security configuration
    enable_authentication: bool = False
    auth_token_expiry: int = 3600  # 1 hour
    max_login_attempts: int = 5
    session_timeout: int = 1800  # 30 minutes
    
    # Database configuration
    database_url: Optional[str] = None
    database_pool_size: int = 10
    database_timeout: int = 30
    database_backup_enabled: bool = True
    database_backup_interval: int = 86400  # 24 hours
    
    # Environment-specific overrides
    environment: str = "development"
    debug_mode: bool = False
    test_mode: bool = False


class ConfigurationManager:
    """
    Comprehensive configuration management system
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.logger = logging.getLogger("botted_library.config")
        
        # Configuration storage
        self._config: ConfigurationSchema = ConfigurationSchema()
        self._config_sources: Dict[str, ConfigurationSource] = {}
        self._validation_rules: List[ValidationRule] = []
        self._change_callbacks: List[Callable[[str, Any, Any], None]] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Configuration history
        self._config_history: List[Dict[str, Any]] = []
        self._max_history_size = 100
        
        self._setup_validation_rules()
        self._load_configuration()
    
    def _setup_validation_rules(self):
        """Setup configuration validation rules"""
        self._validation_rules = [
            # Server validation
            ValidationRule(
                "server_port",
                lambda x: isinstance(x, int) and 1024 <= x <= 65535,
                "Server port must be between 1024 and 65535"
            ),
            ValidationRule(
                "server_max_connections",
                lambda x: isinstance(x, int) and x > 0,
                "Server max connections must be positive"
            ),
            
            # Worker validation
            ValidationRule(
                "max_workers_per_type",
                lambda x: isinstance(x, dict) and all(
                    isinstance(k, str) and isinstance(v, int) and v > 0 
                    for k, v in x.items()
                ),
                "Worker limits must be positive integers"
            ),
            ValidationRule(
                "worker_timeout",
                lambda x: isinstance(x, int) and x > 0,
                "Worker timeout must be positive"
            ),
            
            # Performance validation
            ValidationRule(
                "worker_max_cpu_percent",
                lambda x: isinstance(x, (int, float)) and 0 < x <= 100,
                "CPU percentage must be between 0 and 100"
            ),
            ValidationRule(
                "worker_max_memory_mb",
                lambda x: isinstance(x, int) and x > 0,
                "Memory limit must be positive"
            ),
            
            # Monitoring validation
            ValidationRule(
                "monitoring_interval",
                lambda x: isinstance(x, int) and x > 0,
                "Monitoring interval must be positive"
            ),
            
            # Log level validation
            ValidationRule(
                "log_level",
                lambda x: x.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "Log level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL"
            )
        ]
    
    def _load_configuration(self):
        """Load configuration from all sources"""
        with self._lock:
            # Start with defaults
            self._config = ConfigurationSchema()
            
            # Load from file if specified
            if self.config_file:
                self._load_from_file(self.config_file)
            
            # Load from environment variables
            self._load_from_environment()
            
            # Apply environment-specific overrides
            self._apply_environment_overrides()
            
            # Validate configuration
            self._validate_configuration()
            
            # Save to history
            self._save_to_history("Initial load")
    
    def _load_from_file(self, file_path: str):
        """Load configuration from JSON file"""
        try:
            path = Path(file_path).expanduser()
            if not path.exists():
                self.logger.warning(f"Configuration file not found: {file_path}")
                return
            
            with open(path, 'r') as f:
                file_config = json.load(f)
            
            # Apply file configuration
            for key, value in file_config.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
                    self._config_sources[key] = ConfigurationSource.FILE
                else:
                    self.logger.warning(f"Unknown configuration key in file: {key}")
            
            self.logger.info(f"Configuration loaded from file: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration file {file_path}: {e}")
            raise ConfigurationError(f"Failed to load configuration file: {e}")
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        env_mappings = {
            "BOTTED_SERVER_HOST": "server_host",
            "BOTTED_SERVER_PORT": ("server_port", int),
            "BOTTED_SERVER_MAX_CONNECTIONS": ("server_max_connections", int),
            "BOTTED_SERVER_TIMEOUT": ("server_timeout", int),
            "BOTTED_SERVER_SSL_ENABLED": ("server_ssl_enabled", lambda x: x.lower() == "true"),
            
            "BOTTED_MAX_PLANNERS": ("max_workers_per_type.PLANNER", int),
            "BOTTED_MAX_EXECUTORS": ("max_workers_per_type.EXECUTOR", int),
            "BOTTED_MAX_VERIFIERS": ("max_workers_per_type.VERIFIER", int),
            "BOTTED_WORKER_TIMEOUT": ("worker_timeout", int),
            "BOTTED_WORKER_HEARTBEAT": ("worker_heartbeat_interval", int),
            
            "BOTTED_MAX_SPACES": ("max_collaborative_spaces", int),
            "BOTTED_MAX_PARTICIPANTS": ("max_participants_per_space", int),
            
            "BOTTED_PLUGIN_DIRS": ("plugin_directories", lambda x: x.split(":")),
            "BOTTED_AUTO_LOAD_PLUGINS": ("auto_load_plugins", lambda x: x.lower() == "true"),
            
            "BOTTED_TOOL_TIMEOUT": ("tool_timeout", int),
            "BOTTED_MAX_CONCURRENT_TOOLS": ("max_concurrent_tools", int),
            
            "BOTTED_ENABLE_MONITORING": ("enable_monitoring", lambda x: x.lower() == "true"),
            "BOTTED_MONITORING_INTERVAL": ("monitoring_interval", int),
            
            "BOTTED_LOG_LEVEL": "log_level",
            "BOTTED_LOG_FILE": "log_file_path",
            
            "BOTTED_ENABLE_ERROR_RECOVERY": ("enable_error_recovery", lambda x: x.lower() == "true"),
            "BOTTED_MAX_RETRIES": ("max_retry_attempts", int),
            
            "BOTTED_ENVIRONMENT": "environment",
            "BOTTED_DEBUG": ("debug_mode", lambda x: x.lower() == "true"),
            "BOTTED_TEST_MODE": ("test_mode", lambda x: x.lower() == "true"),
        }
        
        for env_var, config_mapping in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is None:
                continue
            
            try:
                if isinstance(config_mapping, tuple):
                    config_key, converter = config_mapping
                    value = converter(env_value)
                else:
                    config_key = config_mapping
                    value = env_value
                
                # Handle nested keys (e.g., "max_workers_per_type.PLANNER")
                if "." in config_key:
                    parts = config_key.split(".")
                    obj = self._config
                    for part in parts[:-1]:
                        obj = getattr(obj, part)
                    setattr(obj, parts[-1], value)
                else:
                    setattr(self._config, config_key, value)
                
                self._config_sources[config_key] = ConfigurationSource.ENVIRONMENT
                
            except Exception as e:
                self.logger.error(f"Failed to parse environment variable {env_var}={env_value}: {e}")
    
    def _apply_environment_overrides(self):
        """Apply environment-specific configuration overrides"""
        env = self._config.environment.lower()
        
        if env == "production":
            self._config.log_level = "WARNING"
            self._config.debug_mode = False
            self._config.enable_monitoring = True
            self._config.performance_alerts_enabled = True
            self._config.error_notification_enabled = True
            
        elif env == "development":
            self._config.log_level = "DEBUG"
            self._config.debug_mode = True
            self._config.enable_monitoring = True
            self._config.performance_alerts_enabled = False
            
        elif env == "testing":
            self._config.log_level = "ERROR"
            self._config.debug_mode = False
            self._config.test_mode = True
            self._config.enable_monitoring = False
            self._config.database_backup_enabled = False
    
    def _validate_configuration(self):
        """Validate current configuration against rules"""
        errors = []
        
        for rule in self._validation_rules:
            try:
                # Get value using dot notation
                value = self._get_nested_value(self._config, rule.field_path)
                
                if value is None and rule.required:
                    errors.append(f"Required field missing: {rule.field_path}")
                elif value is not None and not rule.validator(value):
                    errors.append(f"{rule.field_path}: {rule.error_message}")
                    
            except Exception as e:
                errors.append(f"Validation error for {rule.field_path}: {e}")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """Get nested value using dot notation"""
        parts = path.split(".")
        current = obj
        
        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _save_to_history(self, reason: str):
        """Save current configuration to history"""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "config": asdict(self._config)
        }
        
        self._config_history.append(history_entry)
        
        # Limit history size
        if len(self._config_history) > self._max_history_size:
            self._config_history.pop(0)
    
    def get_config(self) -> ConfigurationSchema:
        """Get current configuration"""
        with self._lock:
            return self._config
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        with self._lock:
            try:
                return self._get_nested_value(self._config, key) or default
            except Exception:
                return default
    
    def set_value(self, key: str, value: Any, source: ConfigurationSource = ConfigurationSource.RUNTIME):
        """Set configuration value"""
        with self._lock:
            old_value = self.get_value(key)
            
            # Set the value
            parts = key.split(".")
            obj = self._config
            for part in parts[:-1]:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    raise ValueError(f"Invalid configuration path: {key}")
            
            # Set the final value
            final_key = parts[-1]
            if hasattr(obj, final_key):
                setattr(obj, final_key, value)
            elif isinstance(obj, dict):
                obj[final_key] = value
            else:
                raise ValueError(f"Cannot set value for key: {key}")
            
            # Update source tracking
            self._config_sources[key] = source
            
            # Validate after change
            self._validate_configuration()
            
            # Save to history
            self._save_to_history(f"Set {key} = {value}")
            
            # Notify callbacks
            for callback in self._change_callbacks:
                try:
                    callback(key, old_value, value)
                except Exception as e:
                    self.logger.error(f"Configuration change callback failed: {e}")
    
    def reload_configuration(self):
        """Reload configuration from all sources"""
        with self._lock:
            self.logger.info("Reloading configuration...")
            self._load_configuration()
            self.logger.info("Configuration reloaded successfully")
    
    def save_to_file(self, file_path: str):
        """Save current configuration to file"""
        with self._lock:
            try:
                path = Path(file_path).expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
                
                config_dict = asdict(self._config)
                
                with open(path, 'w') as f:
                    json.dump(config_dict, f, indent=2, default=str)
                
                self.logger.info(f"Configuration saved to file: {file_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to save configuration to {file_path}: {e}")
                raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def add_change_callback(self, callback: Callable[[str, Any, Any], None]):
        """Add callback for configuration changes"""
        self._change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[str, Any, Any], None]):
        """Remove configuration change callback"""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        with self._lock:
            return {
                "environment": self._config.environment,
                "server": {
                    "host": self._config.server_host,
                    "port": self._config.server_port,
                    "max_connections": self._config.server_max_connections,
                    "ssl_enabled": self._config.server_ssl_enabled
                },
                "workers": {
                    "max_per_type": self._config.max_workers_per_type,
                    "timeout": self._config.worker_timeout,
                    "heartbeat_interval": self._config.worker_heartbeat_interval
                },
                "monitoring": {
                    "enabled": self._config.enable_monitoring,
                    "interval": self._config.monitoring_interval
                },
                "error_recovery": {
                    "enabled": self._config.enable_error_recovery,
                    "max_retries": self._config.max_retry_attempts
                },
                "plugins": {
                    "auto_load": self._config.auto_load_plugins,
                    "directories": self._config.plugin_directories
                }
            }
    
    def get_configuration_history(self) -> List[Dict[str, Any]]:
        """Get configuration change history"""
        with self._lock:
            return self._config_history.copy()


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None
_config_lock = threading.Lock()


def get_configuration_manager(config_file: Optional[str] = None) -> ConfigurationManager:
    """Get or create global configuration manager"""
    global _config_manager
    
    with _config_lock:
        if _config_manager is None:
            _config_manager = ConfigurationManager(config_file)
        return _config_manager


def get_config() -> ConfigurationSchema:
    """Get current configuration"""
    return get_configuration_manager().get_config()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value by key"""
    return get_configuration_manager().get_value(key, default)


def set_config_value(key: str, value: Any):
    """Set configuration value"""
    get_configuration_manager().set_value(key, value)
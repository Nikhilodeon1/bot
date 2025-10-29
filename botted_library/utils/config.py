"""
Configuration management for the Botted Library

Provides centralized configuration management with support for
file-based configuration, environment variables, and runtime updates.
"""

import json
import os
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path


class ConfigError(Exception):
    """Exception raised for configuration-related errors"""
    pass


class Config:
    """
    Configuration management class with support for hierarchical configuration,
    environment variable overrides, and file-based persistence.
    """
    
    def __init__(self, config_file: Optional[str] = None, auto_load: bool = True):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to configuration file to load
            auto_load: Whether to automatically load default configuration
        """
        self.logger = logging.getLogger(__name__)
        self._config: Dict[str, Any] = {}
        self._config_file: Optional[str] = config_file
        
        # Set up default configuration
        self._setup_defaults()
        
        # Load configuration from file if specified
        if auto_load and config_file:
            try:
                self.load_from_file(config_file)
            except Exception as e:
                self.logger.warning(f"Failed to load config file {config_file}: {str(e)}")
        
        # Override with environment variables
        self._load_from_environment()
    
    def _setup_defaults(self) -> None:
        """Set up default configuration values"""
        self._config = {
            # API Configuration
            'api': {
                'max_workers': 10,
                'default_timeout': 300,
                'enable_metrics': True,
                'log_level': 'INFO'
            },
            
            # Worker Configuration
            'worker_defaults': {
                'max_task_execution_time': 300,
                'memory_context_limit': 10,
                'knowledge_validation_threshold': 0.6,
                'auto_store_task_results': True,
                'enable_progress_tracking': True,
                'clarification_timeout': 60,
                'max_retry_attempts': 3,
                'clear_memory_on_shutdown': False
            },
            
            # Memory System Configuration
            'memory_config': {
                'storage_backend': 'sqlite',
                'database_path': 'botted_library_memory.db',
                'max_short_term_entries': 1000,
                'max_long_term_entries': 10000,
                'cleanup_interval': 3600,  # 1 hour
                'relevance_threshold': 0.1
            },
            
            # Knowledge Validation Configuration
            'knowledge_config': {
                'default_reliability_threshold': 0.6,
                'source_update_frequency': 86400,  # 24 hours
                'cross_reference_limit': 5,
                'validation_cache_size': 1000
            },
            
            # Browser Configuration
            'browser_config': {
                'headless': True,
                'browser_type': 'chrome',
                'window_size': [1920, 1080],
                'page_load_timeout': 30,
                'implicit_wait': 10,
                'download_directory': './downloads',
                'user_agent': None,
                'proxy': None
            },
            
            # Task Executor Configuration
            'task_executor_config': {
                'max_browser_actions': 50,
                'action_timeout': 30,
                'screenshot_on_error': True,
                'retry_failed_actions': True,
                'max_action_retries': 3
            },
            
            # Logging Configuration
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file_path': None,
                'max_file_size': 10485760,  # 10MB
                'backup_count': 5,
                'console_output': True
            },
            
            # Security Configuration
            'security': {
                'trusted_sources': [
                    'wikipedia.org',
                    'github.com',
                    'stackoverflow.com',
                    'docs.python.org',
                    'developer.mozilla.org'
                ],
                'blocked_domains': [],
                'max_file_size': 104857600,  # 100MB
                'allowed_file_types': ['.txt', '.json', '.csv', '.html', '.xml']
            },
            
            # Role-specific Configuration
            'role_config': {
                'editor': {
                    'max_text_length': 100000,
                    'grammar_check_enabled': True,
                    'spell_check_enabled': True,
                    'style_suggestions': True
                },
                'researcher': {
                    'max_sources': 10,
                    'fact_check_enabled': True,
                    'citation_format': 'apa',
                    'search_depth': 3
                },
                'email_checker': {
                    'max_emails_per_batch': 100,
                    'attachment_processing': True,
                    'spam_detection': True,
                    'priority_keywords': ['urgent', 'important', 'asap']
                }
            }
        }
    
    def _load_from_environment(self) -> None:
        """Load configuration overrides from environment variables"""
        try:
            # Map environment variables to config keys
            env_mappings = {
                'BOTTED_LOG_LEVEL': 'logging.level',
                'BOTTED_HEADLESS_BROWSER': 'browser_config.headless',
                'BOTTED_BROWSER_TYPE': 'browser_config.browser_type',
                'BOTTED_MEMORY_BACKEND': 'memory_config.storage_backend',
                'BOTTED_DATABASE_PATH': 'memory_config.database_path',
                'BOTTED_MAX_WORKERS': 'api.max_workers',
                'BOTTED_DEFAULT_TIMEOUT': 'api.default_timeout'
            }
            
            for env_var, config_key in env_mappings.items():
                env_value = os.getenv(env_var)
                if env_value is not None:
                    # Convert string values to appropriate types
                    converted_value = self._convert_env_value(env_value)
                    self.set(config_key, converted_value)
                    self.logger.debug(f"Set {config_key} from environment: {converted_value}")
                    
        except Exception as e:
            self.logger.warning(f"Error loading environment variables: {str(e)}")
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type"""
        # Try boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (supports dot notation like 'api.max_workers')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key.split('.')
            value = self._config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            self.logger.warning(f"Error getting config key {key}: {str(e)}")
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        try:
            keys = key.split('.')
            config = self._config
            
            # Navigate to the parent dictionary
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                elif not isinstance(config[k], dict):
                    raise ConfigError(f"Cannot set {key}: {k} is not a dictionary")
                config = config[k]
            
            # Set the final value
            config[keys[-1]] = value
            self.logger.debug(f"Set config {key} = {value}")
            
        except Exception as e:
            self.logger.error(f"Error setting config key {key}: {str(e)}")
            raise ConfigError(f"Failed to set configuration {key}: {str(e)}")
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration with dictionary values
        
        Args:
            config_dict: Dictionary of configuration values
        """
        try:
            self._deep_update(self._config, config_dict)
            self.logger.debug("Configuration updated with new values")
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {str(e)}")
            raise ConfigError(f"Failed to update configuration: {str(e)}")
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
        """Recursively update nested dictionaries"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def load_from_file(self, file_path: str) -> None:
        """
        Load configuration from JSON file
        
        Args:
            file_path: Path to configuration file
            
        Raises:
            ConfigError: If file cannot be loaded or parsed
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                raise ConfigError(f"Configuration file not found: {file_path}")
            
            with open(path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Validate configuration structure
            if not isinstance(file_config, dict):
                raise ConfigError("Configuration file must contain a JSON object")
            
            # Update configuration
            self.update(file_config)
            self._config_file = file_path
            
            self.logger.info(f"Loaded configuration from {file_path}")
            
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in configuration file {file_path}: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration file {file_path}: {str(e)}")
    
    def save_to_file(self, file_path: Optional[str] = None) -> None:
        """
        Save configuration to JSON file
        
        Args:
            file_path: Path to save configuration (uses loaded file path if None)
            
        Raises:
            ConfigError: If file cannot be saved
        """
        try:
            target_path = file_path or self._config_file
            
            if not target_path:
                raise ConfigError("No file path specified for saving configuration")
            
            path = Path(target_path)
            
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save configuration
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, default=str)
            
            self.logger.info(f"Saved configuration to {target_path}")
            
        except Exception as e:
            raise ConfigError(f"Failed to save configuration to {target_path}: {str(e)}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name
            
        Returns:
            Dictionary containing section configuration
        """
        return self.get(section, {})
    
    def validate(self) -> bool:
        """
        Validate configuration values
        
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigError: If configuration is invalid
        """
        try:
            # Validate required sections exist
            required_sections = ['api', 'worker_defaults', 'memory_config', 'browser_config']
            for section in required_sections:
                if section not in self._config:
                    raise ConfigError(f"Required configuration section missing: {section}")
            
            # Validate specific values
            max_workers = self.get('api.max_workers')
            if not isinstance(max_workers, int) or max_workers <= 0:
                raise ConfigError("api.max_workers must be a positive integer")
            
            timeout = self.get('api.default_timeout')
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ConfigError("api.default_timeout must be a positive number")
            
            # Validate browser configuration
            browser_type = self.get('browser_config.browser_type')
            if browser_type not in ['chrome', 'firefox', 'edge', 'safari']:
                raise ConfigError(f"Invalid browser type: {browser_type}")
            
            # Validate memory configuration
            storage_backend = self.get('memory_config.storage_backend')
            if storage_backend not in ['sqlite', 'memory', 'file']:
                raise ConfigError(f"Invalid memory storage backend: {storage_backend}")
            
            self.logger.debug("Configuration validation passed")
            return True
            
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Configuration validation failed: {str(e)}")
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values"""
        self.logger.info("Resetting configuration to defaults")
        self._setup_defaults()
        self._load_from_environment()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get configuration as dictionary
        
        Returns:
            Copy of configuration dictionary
        """
        return self._config.copy()
    
    def __str__(self) -> str:
        """String representation of configuration"""
        return json.dumps(self._config, indent=2, default=str)
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return f"Config(file={self._config_file}, sections={list(self._config.keys())})"


# Global configuration instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance
    
    Returns:
        Global Config instance
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def set_config(config: Config) -> None:
    """
    Set global configuration instance
    
    Args:
        config: Config instance to set as global
    """
    global _global_config
    _global_config = config


def load_config_file(file_path: str) -> Config:
    """
    Load configuration from file and set as global
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        Loaded Config instance
    """
    config = Config(file_path)
    set_config(config)
    return config
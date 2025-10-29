"""
Component Factory for Botted Library

Provides centralized component creation and dependency injection
with proper error handling and configuration management.
"""

import logging
from typing import Dict, Any, Optional, Type
from datetime import datetime

from .interfaces import (
    IMemorySystem, IKnowledgeValidator, IBrowserController, ITaskExecutor
)
from .memory import MemorySystem
from .knowledge import KnowledgeValidator
from .task_executor import TaskExecutor
from .worker import Worker
from ..browser_interface.browser_controller import BrowserController
# Removed role-specific imports - all workers now use the same underlying system
from .exceptions import (
    BottedLibraryError, ConfigurationError, WorkerError
)
from ..utils.config import Config
from ..utils.logger import setup_logger


class ComponentFactory:
    """
    Factory class for creating and wiring Botted Library components.
    
    Provides centralized dependency injection, configuration management,
    and error handling for all system components.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the component factory.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.logger = setup_logger(__name__)
        
        # Component instances cache
        self._memory_system: Optional[IMemorySystem] = None
        self._knowledge_validator: Optional[IKnowledgeValidator] = None
        self._browser_controller: Optional[IBrowserController] = None
        self._task_executor: Optional[ITaskExecutor] = None
        
        # All workers now use the same underlying system - no role restrictions
        
        # Component creation history for debugging
        self._creation_history: list = []
        
        self.logger.info("Component factory initialized")
    
    def create_memory_system(self, config: Dict[str, Any] = None) -> IMemorySystem:
        """
        Create or return cached memory system instance.
        
        Args:
            config: Optional memory system configuration
            
        Returns:
            IMemorySystem: Memory system instance
            
        Raises:
            ConfigurationError: If memory system creation fails
        """
        if self._memory_system is not None:
            return self._memory_system
        
        try:
            memory_config = {**self.config.get('memory', {})}
            if config:
                memory_config.update(config)
            
            # Set default values
            storage_backend = memory_config.get('storage_backend', 'sqlite')
            db_path = memory_config.get('database_path', 'botted_library_memory.db')
            
            self.logger.info(f"Creating memory system with backend: {storage_backend}")
            
            self._memory_system = MemorySystem(
                storage_backend=storage_backend,
                db_path=db_path
            )
            
            self._record_creation('memory_system', memory_config)
            return self._memory_system
            
        except Exception as e:
            self.logger.error(f"Failed to create memory system: {str(e)}")
            raise ConfigurationError(
                "Memory system creation failed",
                config_key='memory',
                config_value=memory_config,
                original_exception=e
            )
    
    def create_knowledge_validator(self, config: Dict[str, Any] = None) -> IKnowledgeValidator:
        """
        Create or return cached knowledge validator instance.
        
        Args:
            config: Optional knowledge validator configuration
            
        Returns:
            IKnowledgeValidator: Knowledge validator instance
            
        Raises:
            ConfigurationError: If knowledge validator creation fails
        """
        if self._knowledge_validator is not None:
            return self._knowledge_validator
        
        try:
            knowledge_config = {**self.config.get('knowledge', {})}
            if config:
                knowledge_config.update(config)
            
            # Set default values
            db_path = knowledge_config.get('database_path', 'knowledge_validation.db')
            trusted_sources = knowledge_config.get('trusted_sources', [
                'wikipedia.org', 'github.com', 'stackoverflow.com',
                'docs.python.org', 'developer.mozilla.org'
            ])
            
            self.logger.info(f"Creating knowledge validator with {len(trusted_sources)} trusted sources")
            
            self._knowledge_validator = KnowledgeValidator(
                db_path=db_path,
                trusted_sources=trusted_sources,
                config=knowledge_config
            )
            
            self._record_creation('knowledge_validator', knowledge_config)
            return self._knowledge_validator
            
        except Exception as e:
            self.logger.error(f"Failed to create knowledge validator: {str(e)}")
            raise ConfigurationError(
                "Knowledge validator creation failed",
                config_key='knowledge',
                config_value=knowledge_config,
                original_exception=e
            )
    
    def create_browser_controller(self, config: Dict[str, Any] = None) -> IBrowserController:
        """
        Create or return cached browser controller instance.
        
        Args:
            config: Optional browser controller configuration
            
        Returns:
            IBrowserController: Browser controller instance
            
        Raises:
            ConfigurationError: If browser controller creation fails
        """
        if self._browser_controller is not None:
            return self._browser_controller
        
        try:
            browser_config = {**self.config.get('browser', {})}
            if config:
                browser_config.update(config)
            
            # Set default values
            headless = browser_config.get('headless', True)
            browser_type = browser_config.get('browser_type', 'chrome')
            
            self.logger.info(f"Creating browser controller: {browser_type} (headless: {headless})")
            
            self._browser_controller = BrowserController(
                headless=headless,
                browser_type=browser_type
            )
            
            self._record_creation('browser_controller', browser_config)
            return self._browser_controller
            
        except Exception as e:
            self.logger.error(f"Failed to create browser controller: {str(e)}")
            raise ConfigurationError(
                "Browser controller creation failed",
                config_key='browser',
                config_value=browser_config,
                original_exception=e
            )
    
    def create_task_executor(self, config: Dict[str, Any] = None) -> ITaskExecutor:
        """
        Create or return cached task executor instance.
        
        Args:
            config: Optional task executor configuration
            
        Returns:
            ITaskExecutor: Task executor instance
            
        Raises:
            ConfigurationError: If task executor creation fails
        """
        if self._task_executor is not None:
            return self._task_executor
        
        try:
            # Task executor depends on browser controller
            browser_controller = self.create_browser_controller()
            
            task_config = {**self.config.get('task_executor', {})}
            if config:
                task_config.update(config)
            
            self.logger.info("Creating task executor with browser integration")
            
            self._task_executor = TaskExecutor(
                browser_controller=browser_controller
            )
            
            self._record_creation('task_executor', task_config)
            return self._task_executor
            
        except Exception as e:
            self.logger.error(f"Failed to create task executor: {str(e)}")
            raise ConfigurationError(
                "Task executor creation failed",
                config_key='task_executor',
                config_value=task_config,
                original_exception=e
            )
    
    def create_worker(self, worker_id: str, role: str, config: Dict[str, Any] = None) -> Worker:
        """
        Create a fully integrated worker with all dependencies.
        
        Args:
            worker_id: Unique identifier for the worker
            role: Role type for the worker
            config: Optional worker configuration
            
        Returns:
            Worker: Fully configured worker instance
            
        Raises:
            WorkerError: If worker creation fails
            ConfigurationError: If configuration is invalid
        """
        try:
            self.logger.info(f"Creating worker {worker_id} with role {role}")
            
            # All workers use the same underlying system - role is just for context
            
            # Create all required dependencies
            memory_system = self.create_memory_system()
            knowledge_validator = self.create_knowledge_validator()
            browser_controller = self.create_browser_controller()
            task_executor = self.create_task_executor()
            
            # Merge worker configuration
            worker_config = {**self.config.get('worker', {})}
            if config:
                worker_config.update(config)
            
            # Create worker with all dependencies
            worker = Worker(
                memory_system=memory_system,
                knowledge_validator=knowledge_validator,
                browser_controller=browser_controller,
                task_executor=task_executor,
                worker_id=worker_id,
                config=worker_config
            )
            
            # Initialize worker with role
            worker.initialize_role(role)
            
            self._record_creation('worker', {
                'worker_id': worker_id,
                'role': role,
                'config': worker_config
            })
            
            self.logger.info(f"Successfully created worker {worker_id} with role {role}")
            return worker
            
        except Exception as e:
            self.logger.error(f"Failed to create worker {worker_id}: {str(e)}")
            if isinstance(e, (WorkerError, ConfigurationError)):
                raise
            else:
                raise WorkerError(
                    f"Worker creation failed: {str(e)}",
                    worker_id=worker_id,
                    role=role,
                    original_exception=e
                )
    
    def create_role_instance(self, role: str, config: Dict[str, Any] = None):
        """
        Create a role instance - simplified since all workers have the same capabilities.
        
        Args:
            role: Role name (used for context only)
            config: Optional role configuration
            
        Returns:
            Generic role instance
        """
        try:
            role_config = {**self.config.get('roles', {}).get(role, {})}
            if config:
                role_config.update(config)
            
            self.logger.info(f"Creating role instance: {role}")
            
            # Create a simple role object since all workers have the same capabilities
            class GenericRole:
                def __init__(self, role_name, config):
                    self.role = role_name
                    self.config = config
                    
                def get_capabilities(self):
                    return ['all_tools_available']
                    
                def validate_task_compatibility(self, task):
                    return True  # All workers can handle any task
            
            role_instance = GenericRole(role, role_config)
            
            self._record_creation('role', {
                'role_type': role,
                'config': role_config
            })
            
            return role_instance
            
        except Exception as e:
            self.logger.error(f"Failed to create role {role}: {str(e)}")
            raise ConfigurationError(
                f"Role creation failed: {str(e)}",
                config_key='role',
                config_value=role,
                original_exception=e
            )
    
    def register_role(self, role_name: str, role_class=None) -> None:
        """
        Register a custom role class.
        
        Args:
            role_name: Name of the role
            role_class: Role class to register
        """
        self.logger.info(f"Registering custom role: {role_name}")
        # All workers have the same capabilities now
    
    def get_available_roles(self) -> list:
        """Get list of available role names."""
        return ['any_role_name_is_valid']
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the current configuration.
        
        Returns:
            Dict with validation results
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'config_summary': {}
        }
        
        try:
            # Validate memory configuration
            memory_config = self.config.get('memory', {})
            if 'database_path' in memory_config:
                validation_results['config_summary']['memory_db'] = memory_config['database_path']
            
            # Validate knowledge configuration
            knowledge_config = self.config.get('knowledge', {})
            trusted_sources = knowledge_config.get('trusted_sources', [])
            if len(trusted_sources) == 0:
                validation_results['warnings'].append("No trusted sources configured for knowledge validation")
            validation_results['config_summary']['trusted_sources_count'] = len(trusted_sources)
            
            # Validate browser configuration
            browser_config = self.config.get('browser', {})
            browser_type = browser_config.get('browser_type', 'chrome')
            if browser_type not in ['chrome', 'firefox', 'edge']:
                validation_results['warnings'].append(f"Unusual browser type: {browser_type}")
            validation_results['config_summary']['browser_type'] = browser_type
            
            # Skip role validation since all workers have the same capabilities
            roles_config = self.config.get('roles', {})
            # All roles are valid now
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Configuration validation failed: {str(e)}")
        
        return validation_results
    
    def get_creation_history(self) -> list:
        """Get history of component creation for debugging."""
        return self._creation_history.copy()
    
    def reset_components(self) -> None:
        """Reset all cached components (useful for testing)."""
        self.logger.info("Resetting all cached components")
        
        # Close browser if open
        if self._browser_controller:
            try:
                self._browser_controller.close_browser()
            except Exception as e:
                self.logger.warning(f"Error closing browser during reset: {str(e)}")
        
        # Clear component cache
        self._memory_system = None
        self._knowledge_validator = None
        self._browser_controller = None
        self._task_executor = None
        
        # Clear creation history
        self._creation_history.clear()
    
    def _record_creation(self, component_type: str, config: Dict[str, Any]) -> None:
        """Record component creation for debugging and monitoring."""
        creation_record = {
            'component_type': component_type,
            'timestamp': datetime.now().isoformat(),
            'config': config
        }
        self._creation_history.append(creation_record)
    
    def get_component_status(self) -> Dict[str, Any]:
        """Get status of all components."""
        return {
            'memory_system_created': self._memory_system is not None,
            'knowledge_validator_created': self._knowledge_validator is not None,
            'browser_controller_created': self._browser_controller is not None,
            'task_executor_created': self._task_executor is not None,
            'available_roles': ['any_role_name_is_valid'],
            'creation_history_count': len(self._creation_history),
            'factory_config': self.config
        }


# Global factory instance for convenience
_default_factory = None


def get_default_factory() -> ComponentFactory:
    """Get or create the default component factory."""
    global _default_factory
    if _default_factory is None:
        _default_factory = ComponentFactory()
    return _default_factory


def create_worker_with_factory(worker_id: str, role: str, config: Dict[str, Any] = None) -> Worker:
    """Create a worker using the default factory."""
    factory = get_default_factory()
    return factory.create_worker(worker_id, role, config)


def reset_default_factory() -> None:
    """Reset the default factory (useful for testing)."""
    global _default_factory
    if _default_factory:
        _default_factory.reset_components()
        _default_factory = None
"""
System Integration Module for Botted Library v2

This module provides the main integration point for all collaborative features,
managing component dependencies, initialization, and system lifecycle.
"""

import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from .collaborative_server import CollaborativeServer
from .enhanced_worker_registry import EnhancedWorkerRegistry
from .mode_manager import ModeManager
from .plugin_system import PluginManager, get_plugin_manager
from .enhanced_tools import EnhancedToolManager, get_enhanced_tool_manager
from .monitoring_system import MonitoringSystem
from .error_recovery import ErrorRecoverySystem
from .interfaces import WorkerType
from .configuration_manager import ConfigurationManager, ConfigurationSchema, get_configuration_manager


class SystemState(Enum):
    """System state enumeration"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SystemConfiguration:
    """Comprehensive system configuration"""
    # Server configuration
    server_host: str = "localhost"
    server_port: int = 8765
    server_max_connections: int = 100
    
    # Worker configuration
    max_workers_per_type: Dict[WorkerType, int] = field(default_factory=lambda: {
        WorkerType.PLANNER: 5,
        WorkerType.EXECUTOR: 20,
        WorkerType.VERIFIER: 10
    })
    
    # Collaborative spaces configuration
    max_collaborative_spaces: int = 50
    max_participants_per_space: int = 20
    
    # Plugin system configuration
    plugin_directories: List[str] = field(default_factory=lambda: ["plugins", "~/.botted_library/plugins"])
    auto_load_plugins: bool = True
    
    # Enhanced tools configuration
    tool_timeout: int = 300  # 5 minutes
    max_concurrent_tools: int = 10
    
    # Monitoring configuration
    enable_monitoring: bool = True
    monitoring_interval: int = 30  # seconds
    log_level: str = "INFO"
    
    # Error recovery configuration
    enable_error_recovery: bool = True
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Performance configuration
    message_queue_size: int = 1000
    worker_heartbeat_interval: int = 60  # seconds
    cleanup_interval: int = 300  # 5 minutes


class SystemIntegration:
    """
    Main system integration class that manages all v2 collaborative components
    """
    
    def __init__(self, config: Optional[SystemConfiguration] = None, config_file: Optional[str] = None):
        """Initialize system integration with configuration"""
        # Initialize configuration manager
        self.config_manager = get_configuration_manager(config_file)
        
        # Use provided config or get from manager
        if config:
            # Convert SystemConfiguration to ConfigurationSchema if needed
            if isinstance(config, SystemConfiguration):
                self.config = self._convert_system_config(config)
            else:
                self.config = config
        else:
            self.config = self.config_manager.get_config()
        
        self.state = SystemState.UNINITIALIZED
        self.logger = self._setup_logging()
        
        # Core components
        self.server: Optional[CollaborativeServer] = None
        self.worker_registry: Optional[EnhancedWorkerRegistry] = None
        self.mode_manager: Optional[ModeManager] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.tool_manager: Optional[EnhancedToolManager] = None
        self.monitoring_system: Optional[MonitoringSystem] = None
        self.error_recovery: Optional[ErrorRecoverySystem] = None
        
        # System management
        self._shutdown_event = threading.Event()
        self._background_tasks: List[threading.Thread] = []
        self._component_dependencies: Dict[str, List[str]] = {}
        self._initialization_callbacks: List[Callable] = []
        self._shutdown_callbacks: List[Callable] = []
        
        self._setup_component_dependencies()
    
    def _convert_system_config(self, sys_config: SystemConfiguration) -> 'ConfigurationSchema':
        """Convert SystemConfiguration to ConfigurationSchema"""
        from .configuration_manager import ConfigurationSchema
        
        # Create new schema with values from system config
        schema = ConfigurationSchema()
        
        # Map common fields
        schema.server_host = sys_config.server_host
        schema.server_port = sys_config.server_port
        schema.server_max_connections = sys_config.server_max_connections
        
        # Convert worker type dict
        schema.max_workers_per_type = {
            wt.value: count for wt, count in sys_config.max_workers_per_type.items()
        }
        
        schema.max_collaborative_spaces = sys_config.max_collaborative_spaces
        schema.max_participants_per_space = sys_config.max_participants_per_space
        schema.plugin_directories = sys_config.plugin_directories
        schema.auto_load_plugins = sys_config.auto_load_plugins
        schema.tool_timeout = sys_config.tool_timeout
        schema.max_concurrent_tools = sys_config.max_concurrent_tools
        schema.enable_monitoring = sys_config.enable_monitoring
        schema.monitoring_interval = sys_config.monitoring_interval
        schema.log_level = sys_config.log_level
        schema.enable_error_recovery = sys_config.enable_error_recovery
        schema.max_retry_attempts = sys_config.max_retry_attempts
        schema.retry_delay = sys_config.retry_delay
        schema.message_queue_size = sys_config.message_queue_size
        schema.worker_heartbeat_interval = sys_config.worker_heartbeat_interval
        schema.cleanup_interval = sys_config.cleanup_interval
        
        return schema
    
    def _setup_logging(self) -> logging.Logger:
        """Setup system logging"""
        logger = logging.getLogger("botted_library.system")
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _setup_component_dependencies(self):
        """Define component initialization dependencies"""
        self._component_dependencies = {
            "error_recovery": [],
            "monitoring_system": ["error_recovery"],
            "plugin_manager": ["error_recovery"],
            "tool_manager": ["plugin_manager", "error_recovery"],
            "worker_registry": ["error_recovery", "monitoring_system"],
            "server": ["worker_registry", "error_recovery", "monitoring_system"],
            "mode_manager": ["server", "worker_registry", "tool_manager"]
        }
    
    async def initialize_system(self) -> bool:
        """
        Initialize the entire v2 system with proper dependency management
        """
        if self.state != SystemState.UNINITIALIZED:
            self.logger.warning(f"System already initialized (state: {self.state})")
            return False
        
        self.state = SystemState.INITIALIZING
        self.logger.info("Starting system initialization...")
        
        try:
            # Initialize components in dependency order
            await self._initialize_error_recovery()
            await self._initialize_monitoring_system()
            await self._initialize_plugin_manager()
            await self._initialize_tool_manager()
            await self._initialize_worker_registry()
            await self._initialize_server()
            await self._initialize_mode_manager()
            
            # Start background tasks
            self._start_background_tasks()
            
            # Run initialization callbacks
            for callback in self._initialization_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Initialization callback failed: {e}")
            
            self.state = SystemState.RUNNING
            self.logger.info("System initialization completed successfully")
            return True
            
        except Exception as e:
            self.state = SystemState.ERROR
            self.logger.error(f"System initialization failed: {e}")
            await self.shutdown_system()
            return False
    
    async def _initialize_error_recovery(self):
        """Initialize error recovery system"""
        self.logger.debug("Initializing error recovery system...")
        self.error_recovery = ErrorRecoverySystem(
            max_retry_attempts=self.config.max_retry_attempts,
            retry_delay=self.config.retry_delay,
            enabled=self.config.enable_error_recovery
        )
        await self.error_recovery.initialize()
    
    async def _initialize_monitoring_system(self):
        """Initialize monitoring system"""
        self.logger.debug("Initializing monitoring system...")
        self.monitoring_system = MonitoringSystem(
            enabled=self.config.enable_monitoring,
            monitoring_interval=self.config.monitoring_interval
        )
        await self.monitoring_system.initialize()
    
    async def _initialize_plugin_manager(self):
        """Initialize plugin manager"""
        self.logger.debug("Initializing plugin manager...")
        self.plugin_manager = get_plugin_manager()
        
        if self.config.auto_load_plugins:
            for directory in self.config.plugin_directories:
                await self.plugin_manager.load_plugins_from_directory(directory)
    
    async def _initialize_tool_manager(self):
        """Initialize enhanced tool manager"""
        self.logger.debug("Initializing tool manager...")
        self.tool_manager = get_enhanced_tool_manager()
        self.tool_manager.set_timeout(self.config.tool_timeout)
        self.tool_manager.set_max_concurrent(self.config.max_concurrent_tools)
    
    async def _initialize_worker_registry(self):
        """Initialize enhanced worker registry"""
        self.logger.debug("Initializing worker registry...")
        self.worker_registry = EnhancedWorkerRegistry(
            max_workers_per_type=self.config.max_workers_per_type,
            monitoring_system=self.monitoring_system,
            error_recovery=self.error_recovery
        )
        await self.worker_registry.initialize()
    
    async def _initialize_server(self):
        """Initialize collaborative server"""
        self.logger.debug("Initializing collaborative server...")
        self.server = CollaborativeServer(
            host=self.config.server_host,
            port=self.config.server_port,
            max_connections=self.config.server_max_connections,
            worker_registry=self.worker_registry,
            monitoring_system=self.monitoring_system,
            error_recovery=self.error_recovery
        )
        await self.server.start_server()
    
    async def _initialize_mode_manager(self):
        """Initialize mode manager"""
        self.logger.debug("Initializing mode manager...")
        self.mode_manager = ModeManager(
            server=self.server,
            worker_registry=self.worker_registry,
            tool_manager=self.tool_manager
        )
        await self.mode_manager.initialize()
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        if self.config.enable_monitoring and self.monitoring_system:
            monitor_thread = threading.Thread(
                target=self._run_monitoring_loop,
                daemon=True,
                name="MonitoringLoop"
            )
            monitor_thread.start()
            self._background_tasks.append(monitor_thread)
        
        # Start cleanup task
        cleanup_thread = threading.Thread(
            target=self._run_cleanup_loop,
            daemon=True,
            name="CleanupLoop"
        )
        cleanup_thread.start()
        self._background_tasks.append(cleanup_thread)
        
        # Start heartbeat task
        heartbeat_thread = threading.Thread(
            target=self._run_heartbeat_loop,
            daemon=True,
            name="HeartbeatLoop"
        )
        heartbeat_thread.start()
        self._background_tasks.append(heartbeat_thread)
    
    def _run_monitoring_loop(self):
        """Background monitoring loop"""
        while not self._shutdown_event.is_set():
            try:
                if self.monitoring_system:
                    self.monitoring_system.collect_metrics()
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
            
            self._shutdown_event.wait(self.config.monitoring_interval)
    
    def _run_cleanup_loop(self):
        """Background cleanup loop"""
        while not self._shutdown_event.is_set():
            try:
                self._perform_system_cleanup()
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
            
            self._shutdown_event.wait(self.config.cleanup_interval)
    
    def _run_heartbeat_loop(self):
        """Background heartbeat loop"""
        while not self._shutdown_event.is_set():
            try:
                if self.worker_registry:
                    self.worker_registry.send_heartbeat_to_all_workers()
            except Exception as e:
                self.logger.error(f"Heartbeat loop error: {e}")
            
            self._shutdown_event.wait(self.config.worker_heartbeat_interval)
    
    def _perform_system_cleanup(self):
        """Perform system cleanup tasks"""
        if self.server:
            self.server.cleanup_inactive_connections()
        
        if self.worker_registry:
            self.worker_registry.cleanup_inactive_workers()
        
        if self.monitoring_system:
            self.monitoring_system.cleanup_old_metrics()
    
    async def shutdown_system(self) -> bool:
        """
        Gracefully shutdown the entire system
        """
        if self.state in [SystemState.STOPPED, SystemState.STOPPING]:
            self.logger.warning(f"System already stopping/stopped (state: {self.state})")
            return True
        
        self.state = SystemState.STOPPING
        self.logger.info("Starting system shutdown...")
        
        try:
            # Signal background tasks to stop
            self._shutdown_event.set()
            
            # Run shutdown callbacks
            for callback in self._shutdown_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Shutdown callback failed: {e}")
            
            # Shutdown components in reverse dependency order
            if self.mode_manager:
                await self.mode_manager.shutdown()
            
            if self.server:
                await self.server.stop_server()
            
            if self.worker_registry:
                await self.worker_registry.shutdown()
            
            if self.tool_manager:
                await self.tool_manager.shutdown()
            
            if self.plugin_manager:
                await self.plugin_manager.shutdown()
            
            if self.monitoring_system:
                await self.monitoring_system.shutdown()
            
            if self.error_recovery:
                await self.error_recovery.shutdown()
            
            # Wait for background tasks to complete
            for task in self._background_tasks:
                if task.is_alive():
                    task.join(timeout=5.0)
            
            self.state = SystemState.STOPPED
            self.logger.info("System shutdown completed successfully")
            return True
            
        except Exception as e:
            self.state = SystemState.ERROR
            self.logger.error(f"System shutdown failed: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "state": self.state.value,
            "components": {},
            "metrics": {},
            "configuration": {
                "server_host": self.config.server_host,
                "server_port": self.config.server_port,
                "max_workers": self.config.max_workers_per_type,
                "monitoring_enabled": self.config.enable_monitoring,
                "error_recovery_enabled": self.config.enable_error_recovery
            }
        }
        
        # Component status
        if self.server:
            status["components"]["server"] = self.server.get_status()
        
        if self.worker_registry:
            status["components"]["worker_registry"] = self.worker_registry.get_status()
        
        if self.mode_manager:
            status["components"]["mode_manager"] = self.mode_manager.get_status()
        
        if self.monitoring_system:
            status["metrics"] = self.monitoring_system.get_current_metrics()
        
        return status
    
    def add_initialization_callback(self, callback: Callable):
        """Add callback to run after system initialization"""
        self._initialization_callbacks.append(callback)
    
    def add_shutdown_callback(self, callback: Callable):
        """Add callback to run before system shutdown"""
        self._shutdown_callbacks.append(callback)
    
    def is_running(self) -> bool:
        """Check if system is running"""
        return self.state == SystemState.RUNNING
    
    def get_server(self) -> Optional[CollaborativeServer]:
        """Get the collaborative server instance"""
        return self.server
    
    def get_worker_registry(self) -> Optional[EnhancedWorkerRegistry]:
        """Get the worker registry instance"""
        return self.worker_registry
    
    def get_mode_manager(self) -> Optional[ModeManager]:
        """Get the mode manager instance"""
        return self.mode_manager


# Global system instance
_system_instance: Optional[SystemIntegration] = None
_system_lock = threading.Lock()


def get_system_integration(config: Optional[SystemConfiguration] = None) -> SystemIntegration:
    """
    Get or create the global system integration instance
    """
    global _system_instance
    
    with _system_lock:
        if _system_instance is None:
            _system_instance = SystemIntegration(config)
        return _system_instance


def initialize_v2_system(config: Optional[SystemConfiguration] = None) -> SystemIntegration:
    """
    Initialize the v2 collaborative system
    """
    system = get_system_integration(config)
    
    # Run initialization in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        success = loop.run_until_complete(system.initialize_system())
        if not success:
            raise RuntimeError("Failed to initialize v2 system")
        return system
    finally:
        loop.close()


def shutdown_v2_system() -> bool:
    """
    Shutdown the v2 collaborative system
    """
    global _system_instance
    
    if _system_instance is None:
        return True
    
    # Run shutdown in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        success = loop.run_until_complete(_system_instance.shutdown_system())
        with _system_lock:
            _system_instance = None
        return success
    finally:
        loop.close()
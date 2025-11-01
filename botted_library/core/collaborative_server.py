"""
Collaborative Server for Botted Library v2

The CollaborativeServer acts as the central "office building" where all workers
operate and communicate. It manages worker registration, message routing,
and collaborative spaces.
"""

import asyncio
import threading
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .exceptions import WorkerError


class ServerState(Enum):
    """Server lifecycle states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServerConfig:
    """Configuration for the collaborative server"""
    host: str = "localhost"
    port: int = 8765
    max_workers: int = 100
    message_queue_size: int = 1000
    heartbeat_interval: int = 30
    auto_cleanup: bool = True
    log_level: str = "INFO"


class CollaborativeServer:
    """
    Central server that manages worker collaboration and communication.
    
    The server provides:
    - Worker registration and lifecycle management
    - Message routing between workers
    - Collaborative space management
    - Resource coordination and conflict resolution
    """
    
    def __init__(self, config: Optional[ServerConfig] = None):
        """
        Initialize the collaborative server.
        
        Args:
            config: Server configuration, uses defaults if not provided
        """
        self.config = config or ServerConfig()
        self.server_id = str(uuid.uuid4())
        self.state = ServerState.STOPPED
        
        # Setup logging
        self.logger = logging.getLogger(f"CollaborativeServer.{self.server_id[:8]}")
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # Core server components
        self._worker_registry = None  # Will be set during startup
        self._message_router = None   # Will be set during startup
        self._collaborative_space_manager = None  # Will be set during startup
        self._error_recovery_system = None  # Will be set during startup
        self._monitoring_system = None  # Will be set during startup
        
        # Server lifecycle management
        self._server_thread = None
        self._shutdown_event = threading.Event()
        self._startup_complete = threading.Event()
        
        # Statistics and monitoring
        self.start_time = None
        self.stats = {
            'workers_registered': 0,
            'messages_routed': 0,
            'spaces_created': 0,
            'uptime_seconds': 0
        }
        
        self.logger.info(f"CollaborativeServer initialized with ID: {self.server_id[:8]}")
    
    def start_server(self) -> None:
        """
        Start the collaborative server.
        
        Raises:
            WorkerError: If server is already running or fails to start
        """
        if self.state != ServerState.STOPPED:
            raise WorkerError(
                f"Cannot start server in state: {self.state.value}",
                worker_id=self.server_id,
                context={'operation': 'start_server'}
            )
        
        self.logger.info("Starting collaborative server...")
        self.state = ServerState.STARTING
        
        try:
            # Initialize core components
            self._initialize_components()
            
            # Start server in background thread
            self._server_thread = threading.Thread(
                target=self._run_server_loop,
                name=f"CollaborativeServer-{self.server_id[:8]}"
            )
            self._server_thread.daemon = True
            self._server_thread.start()
            
            # Wait for startup to complete
            if not self._startup_complete.wait(timeout=10):
                raise WorkerError(
                    "Server startup timeout",
                    worker_id=self.server_id,
                    context={'operation': 'start_server', 'timeout': 10}
                )
            
            self.start_time = datetime.now()
            self.state = ServerState.RUNNING
            self.logger.info(f"Collaborative server started successfully on {self.config.host}:{self.config.port}")
            
        except Exception as e:
            self.state = ServerState.ERROR
            self.logger.error(f"Failed to start server: {e}")
            raise WorkerError(
                f"Server startup failed: {e}",
                worker_id=self.server_id,
                context={'operation': 'start_server', 'error': str(e)}
            )
    
    def stop_server(self) -> None:
        """
        Gracefully stop the collaborative server.
        
        Raises:
            WorkerError: If server is not running or fails to stop
        """
        if self.state != ServerState.RUNNING:
            self.logger.warning(f"Attempting to stop server in state: {self.state.value}")
            return
        
        self.logger.info("Stopping collaborative server...")
        self.state = ServerState.STOPPING
        
        try:
            # Signal shutdown
            self._shutdown_event.set()
            
            # Wait for server thread to complete
            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=5)
                if self._server_thread.is_alive():
                    self.logger.warning("Server thread did not stop gracefully")
            
            # Cleanup components
            self._cleanup_components()
            
            self.state = ServerState.STOPPED
            self.logger.info("Collaborative server stopped successfully")
            
        except Exception as e:
            self.state = ServerState.ERROR
            self.logger.error(f"Error during server shutdown: {e}")
            raise WorkerError(
                f"Server shutdown failed: {e}",
                worker_id=self.server_id,
                context={'operation': 'stop_server', 'error': str(e)}
            )
    
    def register_worker(self, worker_id: str, worker_info: Dict[str, Any]) -> str:
        """
        Register a worker with the server.
        
        Args:
            worker_id: Unique identifier for the worker
            worker_info: Worker metadata (name, role, capabilities, etc.)
            
        Returns:
            Registration confirmation ID
            
        Raises:
            WorkerError: If server is not running or registration fails
        """
        if self.state != ServerState.RUNNING:
            raise WorkerError(
                f"Cannot register worker - server not running (state: {self.state.value})",
                worker_id=worker_id,
                context={'operation': 'register_worker'}
            )
        
        if not self._worker_registry:
            raise WorkerError(
                "Worker registry not available",
                worker_id=worker_id,
                context={'operation': 'register_worker'}
            )
        
        try:
            # Register with enhanced worker registry
            registration_id = self._worker_registry.register_specialized_worker(
                worker_id=worker_id,
                worker_info=worker_info
            )
            
            self.stats['workers_registered'] += 1
            self.logger.info(f"Worker registered: {worker_id} ({worker_info.get('name', 'Unknown')})")
            
            return registration_id
            
        except Exception as e:
            self.logger.error(f"Worker registration failed for {worker_id}: {e}")
            raise WorkerError(
                f"Worker registration failed: {e}",
                worker_id=worker_id,
                context={'operation': 'register_worker', 'error': str(e)}
            )
    
    def unregister_worker(self, worker_id: str) -> None:
        """
        Unregister a worker from the server.
        
        Args:
            worker_id: ID of the worker to unregister
            
        Raises:
            WorkerError: If unregistration fails
        """
        if not self._worker_registry:
            self.logger.warning(f"Cannot unregister worker {worker_id} - registry not available")
            return
        
        try:
            self._worker_registry.unregister_worker(worker_id)
            self.logger.info(f"Worker unregistered: {worker_id}")
            
        except Exception as e:
            self.logger.error(f"Worker unregistration failed for {worker_id}: {e}")
            raise WorkerError(
                f"Worker unregistration failed: {e}",
                worker_id=worker_id,
                context={'operation': 'unregister_worker', 'error': str(e)}
            )
    
    def route_message(self, from_worker_id: str, to_worker_id: str, message: Dict[str, Any]) -> bool:
        """
        Route a message between workers.
        
        Args:
            from_worker_id: ID of the sending worker
            to_worker_id: ID of the receiving worker
            message: Message content and metadata
            
        Returns:
            True if message was routed successfully
            
        Raises:
            WorkerError: If message routing fails
        """
        if self.state != ServerState.RUNNING:
            raise WorkerError(
                f"Cannot route message - server not running (state: {self.state.value})",
                worker_id=from_worker_id,
                context={'operation': 'route_message'}
            )
        
        if not self._message_router:
            raise WorkerError(
                "Message router not available",
                worker_id=from_worker_id,
                context={'operation': 'route_message'}
            )
        
        try:
            success = self._message_router.route_message(from_worker_id, to_worker_id, message)
            
            if success:
                self.stats['messages_routed'] += 1
                self.logger.debug(f"Message routed: {from_worker_id} -> {to_worker_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Message routing failed: {from_worker_id} -> {to_worker_id}: {e}")
            raise WorkerError(
                f"Message routing failed: {e}",
                worker_id=from_worker_id,
                context={'operation': 'route_message', 'error': str(e)}
            )
    
    def get_worker_registry(self):
        """
        Get the worker registry instance.
        
        Returns:
            Enhanced worker registry instance
            
        Raises:
            WorkerError: If registry is not available
        """
        if not self._worker_registry:
            raise WorkerError(
                "Worker registry not available",
                worker_id=self.server_id,
                context={'operation': 'get_worker_registry'}
            )
        
        return self._worker_registry
    
    def create_collaborative_space(self, space_name: str, created_by: str,
                                 description: Optional[str] = None,
                                 config: Optional[Dict[str, Any]] = None,
                                 space_id: Optional[str] = None):
        """
        Create a new collaborative space.
        
        Args:
            space_name: Human-readable name for the space
            created_by: Worker ID of the space creator
            description: Optional description of the space
            config: Optional configuration parameters
            space_id: Optional custom space ID
            
        Returns:
            Created CollaborativeSpace instance
            
        Raises:
            WorkerError: If space creation fails
        """
        if self.state != ServerState.RUNNING:
            raise WorkerError(
                f"Cannot create collaborative space - server not running (state: {self.state.value})",
                worker_id=created_by,
                context={'operation': 'create_collaborative_space'}
            )
        
        if not self._collaborative_space_manager:
            raise WorkerError(
                "Collaborative space manager not available",
                worker_id=created_by,
                context={'operation': 'create_collaborative_space'}
            )
        
        try:
            space = self._collaborative_space_manager.create_space(
                name=space_name,
                created_by=created_by,
                description=description,
                config=config,
                space_id=space_id
            )
            
            self.stats['spaces_created'] += 1
            self.logger.info(f"Collaborative space '{space_name}' created by {created_by}")
            
            return space
            
        except Exception as e:
            self.logger.error(f"Collaborative space creation failed: {e}")
            raise WorkerError(
                f"Collaborative space creation failed: {e}",
                worker_id=created_by,
                context={'operation': 'create_collaborative_space', 'error': str(e)}
            )
    
    def get_collaborative_space(self, space_id: str):
        """
        Get a collaborative space by ID.
        
        Args:
            space_id: ID of the space to retrieve
            
        Returns:
            CollaborativeSpace instance or None if not found
        """
        if not self._collaborative_space_manager:
            return None
        
        return self._collaborative_space_manager.get_space(space_id)
    
    def list_collaborative_spaces(self, active_only: bool = True):
        """
        List all collaborative spaces.
        
        Args:
            active_only: If True, only return active spaces
            
        Returns:
            List of collaborative spaces
        """
        if not self._collaborative_space_manager:
            return []
        
        return self._collaborative_space_manager.list_spaces(active_only)
    
    def get_collaborative_space_manager(self):
        """
        Get the collaborative space manager instance.
        
        Returns:
            CollaborativeSpaceManager instance
            
        Raises:
            WorkerError: If manager is not available
        """
        if not self._collaborative_space_manager:
            raise WorkerError(
                "Collaborative space manager not available",
                worker_id=self.server_id,
                context={'operation': 'get_collaborative_space_manager'}
            )
        
        return self._collaborative_space_manager
    
    def get_error_recovery_system(self):
        """
        Get the error recovery system instance.
        
        Returns:
            ErrorRecoverySystem instance
            
        Raises:
            WorkerError: If system is not available
        """
        if not self._error_recovery_system:
            raise WorkerError(
                "Error recovery system not available",
                worker_id=self.server_id,
                context={'operation': 'get_error_recovery_system'}
            )
        
        return self._error_recovery_system
    
    def get_monitoring_system(self):
        """
        Get the monitoring system instance.
        
        Returns:
            MonitoringSystem instance
            
        Raises:
            WorkerError: If system is not available
        """
        if not self._monitoring_system:
            raise WorkerError(
                "Monitoring system not available",
                worker_id=self.server_id,
                context={'operation': 'get_monitoring_system'}
            )
        
        return self._monitoring_system
    
    def get_server_status(self) -> Dict[str, Any]:
        """
        Get current server status and statistics.
        
        Returns:
            Dictionary containing server status information
        """
        uptime = 0
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        status = {
            'server_id': self.server_id,
            'state': self.state.value,
            'uptime_seconds': uptime,
            'config': {
                'host': self.config.host,
                'port': self.config.port,
                'max_workers': self.config.max_workers
            },
            'statistics': {
                **self.stats,
                'uptime_seconds': uptime
            },
            'active_workers': len(self._worker_registry.get_active_workers()) if self._worker_registry else 0,
            'collaborative_spaces': len(self._collaborative_space_manager.spaces) if self._collaborative_space_manager else 0
        }
        
        # Add error recovery system status
        if self._error_recovery_system:
            status['error_recovery'] = self._error_recovery_system.get_system_health()
        
        # Add monitoring system status
        if self._monitoring_system:
            status['monitoring'] = self._monitoring_system.get_system_overview()
        
        return status
    
    def _initialize_components(self) -> None:
        """Initialize server components during startup."""
        # Import here to avoid circular imports
        from .enhanced_worker_registry import EnhancedWorkerRegistry
        from .message_router import MessageRouter
        from .collaborative_space import CollaborativeSpaceManager
        from .error_recovery import ErrorRecoverySystem
        from .monitoring_system import MonitoringSystem
        
        # Initialize enhanced worker registry
        self._worker_registry = EnhancedWorkerRegistry(server_instance=self)
        
        # Initialize message router
        self._message_router = MessageRouter(
            worker_registry=self._worker_registry,
            queue_size=self.config.message_queue_size
        )
        
        # Initialize collaborative space manager
        self._collaborative_space_manager = CollaborativeSpaceManager()
        
        # Initialize error recovery system
        self._error_recovery_system = ErrorRecoverySystem(
            server_instance=self,
            config={
                'max_retry_attempts': 3,
                'retry_delay_base': 1.0,
                'heartbeat_interval': self.config.heartbeat_interval,
                'connection_timeout': 10,
                'task_timeout': 300
            }
        )
        
        # Initialize monitoring system
        self._monitoring_system = MonitoringSystem(
            server_instance=self,
            config={
                'collection_interval': 10,
                'retention_hours': 24,
                'enable_system_monitoring': True,
                'alert_thresholds': {
                    'cpu_usage_percent': {'warning': 80, 'critical': 95},
                    'memory_usage_percent': {'warning': 85, 'critical': 95},
                    'error_rate': {'warning': 5, 'critical': 10}
                }
            }
        )
        
        self.logger.debug("Server components initialized")
    
    def _cleanup_components(self) -> None:
        """Cleanup server components during shutdown."""
        try:
            if self._monitoring_system:
                self._monitoring_system.shutdown()
                self._monitoring_system = None
            
            if self._error_recovery_system:
                self._error_recovery_system.shutdown()
                self._error_recovery_system = None
            
            if self._message_router:
                self._message_router.shutdown()
                self._message_router = None
            
            if self._worker_registry:
                self._worker_registry.shutdown()
                self._worker_registry = None
            
            if self._collaborative_space_manager:
                # Close all active spaces
                for space in self._collaborative_space_manager.list_spaces():
                    space.close_space()
                self._collaborative_space_manager = None
            
            self.logger.debug("Server components cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during component cleanup: {e}")
    
    def _run_server_loop(self) -> None:
        """Main server loop running in background thread."""
        try:
            self.logger.debug("Server loop starting...")
            
            # Signal that startup is complete
            self._startup_complete.set()
            
            # Main server loop
            while not self._shutdown_event.is_set():
                # Perform periodic maintenance
                self._perform_maintenance()
                
                # Wait for shutdown signal or timeout
                if self._shutdown_event.wait(timeout=1.0):
                    break
            
            self.logger.debug("Server loop completed")
            
        except Exception as e:
            self.logger.error(f"Server loop error: {e}")
            self.state = ServerState.ERROR
    
    def _perform_maintenance(self) -> None:
        """Perform periodic server maintenance tasks."""
        try:
            # Update uptime statistics
            if self.start_time:
                self.stats['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()
            
            # Cleanup inactive workers if auto_cleanup is enabled
            if self.config.auto_cleanup and self._worker_registry:
                self._worker_registry.cleanup_inactive_workers()
            
            # Process message queue if needed
            if self._message_router:
                self._message_router.process_pending_messages()
                
        except Exception as e:
            self.logger.error(f"Maintenance error: {e}")


# Global server instance (singleton pattern)
_global_server_instance: Optional[CollaborativeServer] = None
_server_lock = threading.Lock()


def get_global_server(config: Optional[ServerConfig] = None) -> CollaborativeServer:
    """
    Get or create the global collaborative server instance.
    
    Args:
        config: Server configuration (only used on first call)
        
    Returns:
        Global collaborative server instance
    """
    global _global_server_instance
    
    with _server_lock:
        if _global_server_instance is None:
            _global_server_instance = CollaborativeServer(config)
        
        return _global_server_instance


def shutdown_global_server() -> None:
    """Shutdown the global collaborative server instance."""
    global _global_server_instance
    
    with _server_lock:
        if _global_server_instance:
            _global_server_instance.stop_server()
            _global_server_instance = None
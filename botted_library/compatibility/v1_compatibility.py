"""
V1 Compatibility Layer for Botted Library v2

This module provides a compatibility wrapper that maintains the v1 interface
while automatically enabling collaborative features in the background.
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import v1 components
from ..simple_worker import Worker as V1Worker, create_worker as v1_create_worker

# Import v2 collaborative components
from ..core.collaborative_server import get_global_server, ServerConfig
from ..core.enhanced_worker import EnhancedWorker
from ..core.enhanced_worker_registry import WorkerType


class CompatibilityManager:
    """Manages the compatibility layer between v1 and v2 interfaces."""
    
    def __init__(self):
        self._server = None
        self._server_started = False
        self._collaborative_enabled = True
        self._v1_workers = {}  # Track v1 workers for potential upgrade
        self._lock = threading.Lock()
        self.logger = logging.getLogger("V1Compatibility")
        
    def ensure_server_running(self) -> None:
        """Ensure the collaborative server is running for v2 features."""
        with self._lock:
            if not self._server_started and self._collaborative_enabled:
                try:
                    self._server = get_global_server()
                    if self._server.state.value != "running":
                        self._server.start_server()
                    self._server_started = True
                    self.logger.info("Collaborative server started automatically for v1 compatibility")
                except Exception as e:
                    self.logger.warning(f"Failed to start collaborative server: {e}")
                    self._collaborative_enabled = False
    
    def register_v1_worker(self, worker_id: str, worker: 'Worker') -> None:
        """Register a v1 worker for potential collaborative features."""
        self._v1_workers[worker_id] = worker
        
        # If collaborative features are enabled, register with server
        if self._collaborative_enabled and self._server_started:
            try:
                worker_info = {
                    'name': worker.name,
                    'role': worker.role,
                    'job_description': worker.job_description,
                    'worker_type': WorkerType.EXECUTOR,  # Default v1 workers to executor type
                    'capabilities': worker._get_capabilities(),
                    'v1_compatibility': True,
                    'created_at': datetime.now().isoformat()
                }
                self._server.register_worker(worker_id, worker_info)
                self.logger.debug(f"V1 worker {worker.name} registered with collaborative server")
            except Exception as e:
                self.logger.warning(f"Failed to register v1 worker with server: {e}")
    
    def unregister_v1_worker(self, worker_id: str) -> None:
        """Unregister a v1 worker."""
        if worker_id in self._v1_workers:
            del self._v1_workers[worker_id]
        
        if self._server_started and self._server:
            try:
                self._server.unregister_worker(worker_id)
            except Exception as e:
                self.logger.warning(f"Failed to unregister v1 worker: {e}")
    
    def enable_collaborative_features(self) -> bool:
        """Enable collaborative features for v1 workers."""
        with self._lock:
            self._collaborative_enabled = True
            self.ensure_server_running()
            
            # Register existing workers with server
            for worker_id, worker in self._v1_workers.items():
                self.register_v1_worker(worker_id, worker)
            
            return self._server_started
    
    def disable_collaborative_features(self) -> None:
        """Disable collaborative features."""
        with self._lock:
            self._collaborative_enabled = False
            # Note: We don't stop the server as other v2 workers might be using it
    
    def get_status(self) -> Dict[str, Any]:
        """Get compatibility layer status."""
        return {
            'collaborative_enabled': self._collaborative_enabled,
            'server_running': self._server_started,
            'v1_workers_count': len(self._v1_workers),
            'server_status': self._server.get_server_status() if self._server else None
        }


# Global compatibility manager instance
_compatibility_manager = CompatibilityManager()


class Worker:
    """
    V1 Compatible Worker with automatic collaborative features.
    
    This class maintains the exact same interface as the v1 Worker class
    but automatically enables collaborative features in the background.
    """
    
    def __init__(self, name: str, role: str, job_description: str, config: Dict[str, Any] = None):
        """
        Initialize a v1 compatible worker with automatic collaborative features.
        
        Args:
            name: Name for your worker (e.g., "Sarah", "Alex", "DataAnalyst_01")
            role: Their role/title (e.g., "Marketing Manager", "Software Developer")
            job_description: What they do and their expertise
            config: Optional configuration for LLM, browser, etc.
        """
        # Initialize the underlying v1 worker
        self._v1_worker = V1Worker(name, role, job_description, config)
        
        # Expose v1 worker attributes for compatibility
        self.name = self._v1_worker.name
        self.role = self._v1_worker.role
        self.job_description = self._v1_worker.job_description
        self.config = self._v1_worker.config
        
        # Generate unique worker ID for collaborative features
        self._worker_id = self._v1_worker._worker_id
        
        # Automatically enable collaborative features
        _compatibility_manager.ensure_server_running()
        _compatibility_manager.register_v1_worker(self._worker_id, self)
        
        # Add collaborative capabilities message
        if _compatibility_manager._collaborative_enabled and _compatibility_manager._server_started:
            print(f"🚀 Collaborative features automatically enabled for {self.name}")
            print(f"   Can now collaborate with other workers and access shared resources")
    
    def call(self, instructions: str, **kwargs) -> Dict[str, Any]:
        """
        Give the worker a task to complete (v1 compatible interface).
        
        This method maintains exact compatibility with v1 while automatically
        providing collaborative features when available.
        
        Args:
            instructions: What you want the worker to do
            **kwargs: Additional parameters
            
        Returns:
            Dict with results (same format as v1)
        """
        # Check if collaborative features are available
        collaborative_available = (
            _compatibility_manager._collaborative_enabled and 
            _compatibility_manager._server_started
        )
        
        if collaborative_available:
            # Add collaborative context to the task
            enhanced_instructions = self._add_collaborative_context(instructions, kwargs)
            result = self._v1_worker.call(enhanced_instructions, **kwargs)
            
            # Add collaborative metadata to result
            result['collaborative_features_used'] = True
            result['available_collaborators'] = len(self.get_active_workers())
            
        else:
            # Fall back to standard v1 behavior
            result = self._v1_worker.call(instructions, **kwargs)
            result['collaborative_features_used'] = False
        
        return result
    
    def _add_collaborative_context(self, instructions: str, kwargs: Dict[str, Any]) -> str:
        """Add collaborative context to task instructions."""
        try:
            # Get available collaborators
            collaborators = self.get_active_workers()
            
            if collaborators:
                collab_info = []
                for worker in collaborators[:3]:  # Limit to top 3 for brevity
                    collab_info.append(f"{worker['name']} ({worker['role']})")
                
                collaborative_context = f"""
                
COLLABORATIVE CONTEXT:
You can collaborate with these workers if needed: {', '.join(collab_info)}
Use self.delegate_task() or self.ask_for_help() if collaboration would improve results.
                """
                
                return instructions + collaborative_context
        except Exception as e:
            # If collaborative context fails, just use original instructions
            pass
        
        return instructions
    
    # Delegate all other v1 methods to the underlying worker
    def get_history(self) -> List[Dict[str, Any]]:
        """Get the task history for this worker."""
        return self._v1_worker.get_history()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current worker status."""
        status = self._v1_worker.get_status()
        status['collaborative_features'] = _compatibility_manager._collaborative_enabled
        status['server_connected'] = _compatibility_manager._server_started
        return status
    
    def _get_capabilities(self) -> List[str]:
        """Get list of worker capabilities."""
        return self._v1_worker._get_capabilities()
    
    def get_active_workers(self) -> List[Dict[str, Any]]:
        """Get list of other active workers (collaborative feature)."""
        return self._v1_worker.get_active_workers()
    
    def delegate_task(self, task_description: str, preferred_role: str = None, **kwargs) -> Dict[str, Any]:
        """Delegate a task to another worker (collaborative feature)."""
        return self._v1_worker.delegate_task(task_description, preferred_role, **kwargs)
    
    def ask_for_help(self, question: str, preferred_role: str = None) -> str:
        """Ask another worker for help (collaborative feature)."""
        return self._v1_worker.ask_for_help(question, preferred_role)
    
    def get_collaboration_history(self) -> List[Dict[str, Any]]:
        """Get history of collaborations (collaborative feature)."""
        return self._v1_worker.get_collaboration_history()
    
    def shutdown(self):
        """Gracefully shutdown the worker."""
        _compatibility_manager.unregister_v1_worker(self._worker_id)
        self._v1_worker.shutdown()


def create_worker(name: str, role: str, job_description: str, config: Dict[str, Any] = None) -> Worker:
    """
    Create a human-like AI worker with automatic collaborative features.
    
    This function maintains exact compatibility with the v1 create_worker function
    while automatically enabling collaborative features in the background.
    
    Args:
        name: Name for your worker (e.g., "Sarah", "Alex", "DataAnalyst_01")
        role: Their role/title (e.g., "Marketing Manager", "Software Developer")
        job_description: What they do and their expertise
        config: Optional configuration for LLM, browser, etc.
    
    Returns:
        Worker instance with collaborative features enabled
    
    Example:
        # This works exactly like v1 but with collaborative features
        sarah = create_worker(
            name="Sarah",
            role="Marketing Manager", 
            job_description="Specializes in market research and competitive analysis"
        )
        result = sarah.call("Research our top 3 competitors")
    """
    return Worker(name, role, job_description, config)


def enable_collaborative_features() -> bool:
    """
    Explicitly enable collaborative features for all v1 workers.
    
    Returns:
        True if collaborative features were successfully enabled
    """
    return _compatibility_manager.enable_collaborative_features()


def disable_collaborative_features() -> None:
    """
    Disable collaborative features for v1 workers.
    
    Workers will continue to function but without collaborative capabilities.
    """
    _compatibility_manager.disable_collaborative_features()


def get_compatibility_status() -> Dict[str, Any]:
    """
    Get the current status of the v1 compatibility layer.
    
    Returns:
        Dictionary containing compatibility status information
    """
    return _compatibility_manager.get_status()


# Automatic server initialization on module import
def _initialize_compatibility_layer():
    """Initialize the compatibility layer when module is imported."""
    try:
        # Start server automatically but don't fail if it doesn't work
        _compatibility_manager.ensure_server_running()
    except Exception as e:
        # Silently handle initialization failures
        logging.getLogger("V1Compatibility").debug(f"Auto-initialization failed: {e}")


# Initialize on import
_initialize_compatibility_layer()
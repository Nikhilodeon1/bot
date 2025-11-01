"""
Core module for the Botted Library

Contains the main components: Worker, TaskExecutor, MemorySystem, KnowledgeValidator,
and enhanced collaborative features including plugin system and enhanced tools.
"""

from .worker import Worker
from .task_executor import TaskExecutor
from .memory import MemorySystem
from .knowledge import KnowledgeValidator

# Enhanced collaborative components
from .collaborative_server import CollaborativeServer
from .enhanced_worker_registry import EnhancedWorkerRegistry
from .enhanced_worker import EnhancedWorker
from .planner_worker import PlannerWorker
from .executor_worker import ExecutorWorker
from .verifier_worker import VerifierWorker
from .collaborative_space import CollaborativeSpace
from .shared_whiteboard import SharedWhiteboard
from .shared_filesystem import SharedFileSystem
from .message_router import MessageRouter
from .mode_manager import ModeManager
from .manual_mode_controller import ManualModeController
from .auto_mode_controller import AutoModeController

# Plugin system and enhanced tools
from .plugin_system import (
    IPlugin, PluginRegistry, PluginManager, PluginDiscovery,
    get_plugin_registry, get_plugin_manager, get_plugin_discovery
)
from .enhanced_tools import (
    IEnhancedTool, EnhancedToolManager, get_enhanced_tool_manager
)

# System integration and startup
from .system_integration import (
    SystemIntegration, SystemConfiguration, SystemState,
    get_system_integration, initialize_v2_system, shutdown_v2_system
)
from .system_startup import (
    SystemStartup, StartupOptions, create_default_startup,
    create_production_startup, create_development_startup, quick_start_system
)

# Error handling and monitoring
from .error_recovery import ErrorRecoverySystem
from .monitoring_system import MonitoringSystem

__all__ = [
    # Core components
    "Worker",
    "TaskExecutor",
    "MemorySystem", 
    "KnowledgeValidator",
    
    # Collaborative components
    "CollaborativeServer",
    "EnhancedWorkerRegistry",
    "EnhancedWorker",
    "PlannerWorker",
    "ExecutorWorker", 
    "VerifierWorker",
    "CollaborativeSpace",
    "SharedWhiteboard",
    "SharedFileSystem",
    "MessageRouter",
    "ModeManager",
    "ManualModeController",
    "AutoModeController",
    
    # Plugin system
    "IPlugin",
    "PluginRegistry",
    "PluginManager", 
    "PluginDiscovery",
    "get_plugin_registry",
    "get_plugin_manager",
    "get_plugin_discovery",
    
    # Enhanced tools
    "IEnhancedTool",
    "EnhancedToolManager",
    "get_enhanced_tool_manager",
    
    # System integration
    "SystemIntegration",
    "SystemConfiguration", 
    "SystemState",
    "get_system_integration",
    "initialize_v2_system",
    "shutdown_v2_system",
    
    # System startup
    "SystemStartup",
    "StartupOptions",
    "create_default_startup",
    "create_production_startup", 
    "create_development_startup",
    "quick_start_system",
    
    # Error handling and monitoring
    "ErrorRecoverySystem",
    "MonitoringSystem"
]
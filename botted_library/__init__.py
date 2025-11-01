"""
Botted Library - Human-like AI Workers

Create AI workers with specific roles and expertise. Each worker can use any tool 
needed - web search, coding, document creation, email, and more.

Quick Start:
    from botted_library import create_worker
    
    sarah = create_worker(
        name="Sarah",
        role="Marketing Manager", 
        job_description="Expert in market research and strategy"
    )
    result = sarah.call("Research our top 3 competitors and analyze their pricing")
"""

__version__ = "1.0.0"
__author__ = "Botted Library Team"

# Simple interface (recommended for most users) - now with v2 collaborative features
from .compatibility import Worker, create_worker

# V2 System Integration (for collaborative features)
from .core.system_integration import (
    SystemIntegration, SystemConfiguration, get_system_integration,
    initialize_v2_system, shutdown_v2_system
)
from .core.system_startup import (
    SystemStartup, quick_start_system, create_default_startup
)

# Advanced interface (for power users who need fine control)
from .core.worker import Worker as CoreWorker
from .core.task_executor import TaskExecutor
from .core.memory import MemorySystem
from .core.knowledge import KnowledgeValidator
from .core.factory import ComponentFactory, get_default_factory, create_worker_with_factory
from .core.error_handler import ErrorHandler, get_default_error_handler, handle_error

# Import AI components
try:
    from .core.llm_interface import LLMInterface, create_llm_interface
    from .core.reasoning_engine import ReasoningEngine
    from .core.code_executor import CodeExecutor
    _ai_available = True
except ImportError as e:
    # Suppress warning for normal users - they don't need to see this
    _ai_available = False
    LLMInterface = None
    create_llm_interface = None
    ReasoningEngine = None
    CodeExecutor = None

# Main exports (simple interface)
__all__ = [
    # Simple interface (recommended)
    "Worker",
    "create_worker",
    
    # V2 System Integration
    "SystemIntegration",
    "SystemConfiguration", 
    "get_system_integration",
    "initialize_v2_system",
    "shutdown_v2_system",
    "SystemStartup",
    "quick_start_system",
    "create_default_startup",
    
    # Advanced interface
    "CoreWorker",
    "TaskExecutor", 
    "MemorySystem",
    "KnowledgeValidator",
    "ComponentFactory",
    "get_default_factory",
    "create_worker_with_factory",
    "ErrorHandler",
    "get_default_error_handler",
    "handle_error"
]

# Add AI components to __all__ if available
if _ai_available:
    __all__.extend([
        "LLMInterface",
        "create_llm_interface", 
        "ReasoningEngine",
        "CodeExecutor"
    ])
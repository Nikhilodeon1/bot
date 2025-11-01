# Botted Library v2 - API Reference

## Table of Contents

- [System Integration](#system-integration)
- [Worker Management](#worker-management)
- [Collaborative Spaces](#collaborative-spaces)
- [Mode Controllers](#mode-controllers)
- [Configuration Management](#configuration-management)
- [Plugin System](#plugin-system)
- [Enhanced Tools](#enhanced-tools)
- [Error Handling](#error-handling)
- [Monitoring](#monitoring)
- [V1 Compatibility](#v1-compatibility)

## System Integration

### SystemIntegration

Main system orchestrator for all v2 components.

```python
from botted_library.core.system_integration import SystemIntegration, SystemConfiguration

class SystemIntegration:
    def __init__(self, config: Optional[SystemConfiguration] = None, config_file: Optional[str] = None)
    async def initialize_system(self) -> bool
    async def shutdown_system(self) -> bool
    def get_system_status(self) -> Dict[str, Any]
    def is_running(self) -> bool
    def get_server(self) -> Optional[CollaborativeServer]
    def get_worker_registry(self) -> Optional[EnhancedWorkerRegistry]
    def get_mode_manager(self) -> Optional[ModeManager]
    def add_initialization_callback(self, callback: Callable)
    def add_shutdown_callback(self, callback: Callable)
```

**Example Usage:**

```python
# Basic initialization
config = SystemConfiguration(server_port=8765)
system = SystemIntegration(config)
await system.initialize_system()

# Check system status
status = system.get_system_status()
print(f"System state: {status['state']}")

# Graceful shutdown
await system.shutdown_system()
```

### SystemConfiguration

Configuration schema for the system.

```python
@dataclass
class SystemConfiguration:
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
    
    # Collaborative spaces
    max_collaborative_spaces: int = 50
    max_participants_per_space: int = 20
    
    # Plugin system
    plugin_directories: List[str] = field(default_factory=lambda: ["plugins"])
    auto_load_plugins: bool = True
    
    # Enhanced tools
    tool_timeout: int = 300
    max_concurrent_tools: int = 10
    
    # Monitoring
    enable_monitoring: bool = True
    monitoring_interval: int = 30
    log_level: str = "INFO"
    
    # Error recovery
    enable_error_recovery: bool = True
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
```

### SystemStartup

System initialization and startup management.

```python
from botted_library.core.system_startup import SystemStartup, StartupOptions

class SystemStartup:
    def __init__(self, options: Optional[StartupOptions] = None)
    def load_configuration(self) -> SystemConfiguration
    async def start_system(self) -> SystemIntegration
    async def stop_system(self) -> bool
    def validate_system_requirements(self) -> bool

# Convenience functions
async def quick_start_system(config_file: Optional[str] = None) -> SystemIntegration
def create_default_startup() -> SystemStartup
def create_production_startup() -> SystemStartup
def create_development_startup() -> SystemStartup
```

**Example Usage:**

```python
# Quick start
system = await quick_start_system()

# Custom startup
startup = SystemStartup(StartupOptions(
    environment="production",
    log_level="WARNING",
    enable_monitoring=True
))
system = await startup.start_system()
```

## Worker Management

### EnhancedWorkerRegistry

Manages worker lifecycle and capabilities.

```python
from botted_library.core.enhanced_worker_registry import EnhancedWorkerRegistry

class EnhancedWorkerRegistry:
    def __init__(self, max_workers_per_type: Dict[WorkerType, int])
    async def register_worker(self, worker: EnhancedWorker) -> str
    async def unregister_worker(self, worker_id: str) -> bool
    def get_worker(self, worker_id: str) -> Optional[EnhancedWorker]
    def get_workers_by_type(self, worker_type: WorkerType) -> List[EnhancedWorker]
    def get_all_workers(self) -> List[EnhancedWorker]
    def get_available_workers(self, worker_type: WorkerType) -> List[EnhancedWorker]
    async def create_worker(self, worker_type: WorkerType, name: str, **kwargs) -> EnhancedWorker
    def get_worker_count(self, worker_type: Optional[WorkerType] = None) -> int
    def get_status(self) -> Dict[str, Any]
```

### EnhancedWorker

Base class for all v2 workers.

```python
from botted_library.core.enhanced_worker import EnhancedWorker

class EnhancedWorker:
    def __init__(self, worker_id: str, name: str, worker_type: WorkerType)
    
    # Communication
    async def send_message_to_worker(self, recipient_id: str, message: Dict[str, Any])
    async def receive_message(self, sender_id: str, message: Dict[str, Any])
    async def broadcast_message(self, message: Dict[str, Any])
    
    # Collaborative spaces
    async def join_collaborative_space(self, space_id: str)
    async def leave_collaborative_space(self, space_id: str)
    def get_collaborative_spaces(self) -> List[str]
    
    # Tool usage
    async def use_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any
    def get_available_tools(self) -> List[str]
    
    # State management
    def get_state(self) -> Dict[str, Any]
    def update_state(self, state_updates: Dict[str, Any])
    
    # Abstract methods (implemented by subclasses)
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]
    def get_capabilities(self) -> List[str]
```

### PlannerWorker

Strategic planning and coordination worker.

```python
from botted_library.core.planner_worker import PlannerWorker

class PlannerWorker(EnhancedWorker):
    # Strategy creation
    async def create_strategy(self, objective: str) -> Dict[str, Any]
    async def create_execution_plan(self, strategy: Dict[str, Any]) -> Dict[str, Any]
    async def create_office_flowchart(self, objective: str) -> Dict[str, Any]
    
    # Team management
    async def determine_worker_allocation(self, objective: str) -> Dict[str, int]
    async def create_new_worker(self, worker_type: WorkerType, specifications: Dict[str, Any]) -> str
    async def assign_task_to_executor(self, executor_id: str, task: Dict[str, Any])
    
    # Progress monitoring
    async def monitor_progress(self) -> Dict[str, Any]
    async def adapt_strategy(self, progress_data: Dict[str, Any])
    
    # Coordination
    def define_interaction_order(self) -> List[str]
    async def coordinate_team_workflow(self, team_members: List[str])
```

### ExecutorWorker

Task execution and action worker.

```python
from botted_library.core.executor_worker import ExecutorWorker

class ExecutorWorker(EnhancedWorker):
    # Task execution
    async def execute_assigned_task(self, task: Dict[str, Any]) -> Dict[str, Any]
    async def perform_action(self, action_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]
    
    # Progress reporting
    async def report_progress(self, task_id: str, progress: Dict[str, Any])
    async def request_clarification(self, question: str) -> str
    
    # Collaboration
    async def collaborate_with_executor(self, other_executor_id: str, shared_task: Dict[str, Any])
    async def share_intermediate_results(self, results: Dict[str, Any])
```

### VerifierWorker

Quality assurance and validation worker.

```python
from botted_library.core.verifier_worker import VerifierWorker

class VerifierWorker(EnhancedWorker):
    # Quality validation
    async def validate_output(self, output: Dict[str, Any]) -> Dict[str, Any]
    async def check_quality_standards(self, content: Any) -> Dict[str, Any]
    async def approve_for_delivery(self, output: Dict[str, Any]) -> bool
    
    # Feedback generation
    async def generate_improvement_feedback(self, output: Dict[str, Any]) -> Dict[str, Any]
    async def suggest_corrections(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]
    
    # Validation workflows
    async def create_validation_checklist(self, output_type: str) -> List[Dict[str, Any]]
    async def perform_comprehensive_review(self, output: Dict[str, Any]) -> Dict[str, Any]
```

## Collaborative Spaces

### CollaborativeSpace

Shared workspace for team collaboration.

```python
from botted_library.core.collaborative_space import CollaborativeSpace

class CollaborativeSpace:
    def __init__(self, space_id: str, name: str, max_participants: int = 20)
    
    # Participant management
    async def add_participant(self, worker_id: str) -> bool
    async def remove_participant(self, worker_id: str) -> bool
    def get_participants(self) -> List[str]
    def is_participant(self, worker_id: str) -> bool
    
    # Resource access
    def get_shared_whiteboard(self) -> SharedWhiteboard
    def get_shared_filesystem(self) -> SharedFileSystem
    
    # Communication
    async def broadcast_to_participants(self, message: Dict[str, Any])
    async def send_notification(self, recipient_id: str, notification: Dict[str, Any])
    
    # Activity tracking
    def get_activity_log(self) -> List[Dict[str, Any]]
    def log_activity(self, activity: Dict[str, Any])
    
    # Space management
    def get_space_info(self) -> Dict[str, Any]
    async def archive_space(self) -> bool
```

### SharedWhiteboard

Visual collaboration tool.

```python
from botted_library.core.shared_whiteboard import SharedWhiteboard

class SharedWhiteboard:
    def __init__(self, space_id: str)
    
    # Content management
    async def add_content(self, content: Dict[str, Any], author_id: str) -> str
    async def update_content(self, content_id: str, updates: Dict[str, Any], author_id: str) -> bool
    async def remove_content(self, content_id: str, author_id: str) -> bool
    def get_content(self) -> List[Dict[str, Any]]
    
    # Collaboration
    async def collaborate_on_content(self, content_id: str, author_id: str, changes: Dict[str, Any])
    async def add_comment(self, content_id: str, comment: str, author_id: str) -> str
    
    # Version control
    def get_version_history(self) -> List[Dict[str, Any]]
    async def revert_to_version(self, version_id: str) -> bool
    
    # Export
    async def export_whiteboard(self, format: str = "json") -> str
    async def save_snapshot(self, name: str) -> str
```

### SharedFileSystem

Shared file access and management.

```python
from botted_library.core.shared_filesystem import SharedFileSystem

class SharedFileSystem:
    def __init__(self, space_id: str)
    
    # File operations
    async def create_file(self, filename: str, content: str, author_id: str) -> str
    async def read_file(self, file_id: str) -> Dict[str, Any]
    async def update_file(self, file_id: str, content: str, author_id: str) -> bool
    async def delete_file(self, file_id: str, author_id: str) -> bool
    
    # File sharing
    async def share_file(self, file_id: str, participant_ids: List[str]) -> bool
    async def set_file_permissions(self, file_id: str, permissions: Dict[str, str]) -> bool
    def get_file_permissions(self, file_id: str) -> Dict[str, str]
    
    # File discovery
    def list_files(self, author_id: Optional[str] = None) -> List[Dict[str, Any]]
    def search_files(self, query: str) -> List[Dict[str, Any]]
    
    # Version control
    def get_file_history(self, file_id: str) -> List[Dict[str, Any]]
    async def revert_file(self, file_id: str, version_id: str) -> bool
    
    # Collaboration
    async def lock_file(self, file_id: str, user_id: str) -> bool
    async def unlock_file(self, file_id: str, user_id: str) -> bool
    def get_file_locks(self) -> Dict[str, str]
```

## Mode Controllers

### ModeManager

Manages manual and auto operation modes.

```python
from botted_library.core.mode_manager import ModeManager

class ModeManager:
    def __init__(self, server: CollaborativeServer, worker_registry: EnhancedWorkerRegistry)
    
    # Mode management
    async def switch_to_manual_mode(self) -> bool
    async def switch_to_auto_mode(self) -> bool
    def get_current_mode(self) -> str
    
    # Worker creation
    async def create_worker(self, worker_type: WorkerType, name: str, **kwargs) -> EnhancedWorker
    async def create_collaborative_space(self, name: str) -> CollaborativeSpace
    
    # Objective execution (auto mode)
    async def execute_objective(self, objective: str) -> Dict[str, Any]
    
    # Status and monitoring
    def get_status(self) -> Dict[str, Any]
    async def get_active_workflows(self) -> List[Dict[str, Any]]
```

### ManualModeController

User-directed worker and task management.

```python
from botted_library.core.manual_mode_controller import ManualModeController

class ManualModeController:
    # Worker management
    async def create_worker_manually(self, worker_type: WorkerType, specifications: Dict[str, Any]) -> str
    async def assign_task_manually(self, worker_id: str, task: Dict[str, Any])
    async def manage_workflow(self, workflow_definition: Dict[str, Any])
    
    # Space management
    async def create_collaborative_space_manually(self, name: str, participants: List[str]) -> str
    async def configure_space_resources(self, space_id: str, resources: Dict[str, Any])
    
    # Progress tracking
    def get_manual_workflow_status(self) -> Dict[str, Any]
    async def intervene_in_workflow(self, intervention: Dict[str, Any])
```

### AutoModeController

Autonomous planning and execution.

```python
from botted_library.core.auto_mode_controller import AutoModeController

class AutoModeController:
    # Autonomous operations
    async def activate_initial_planner(self, objective: str) -> str
    async def create_additional_planners(self, requirements: Dict[str, Any]) -> List[str]
    async def manage_executor_teams(self, team_specifications: List[Dict[str, Any]]) -> List[str]
    
    # Workflow management
    async def execute_autonomous_workflow(self, objective: str) -> Dict[str, Any]
    async def adapt_workflow_dynamically(self, performance_data: Dict[str, Any])
    
    # Optimization
    async def optimize_team_composition(self, current_performance: Dict[str, Any])
    async def scale_resources_automatically(self, demand_metrics: Dict[str, Any])
```

## Configuration Management

### ConfigurationManager

Comprehensive configuration management.

```python
from botted_library.core.configuration_manager import ConfigurationManager, ConfigurationSchema

class ConfigurationManager:
    def __init__(self, config_file: Optional[str] = None)
    
    # Configuration access
    def get_config(self) -> ConfigurationSchema
    def get_value(self, key: str, default: Any = None) -> Any
    def set_value(self, key: str, value: Any, source: ConfigurationSource = ConfigurationSource.RUNTIME)
    
    # Configuration management
    def reload_configuration(self)
    def save_to_file(self, file_path: str)
    def get_configuration_summary(self) -> Dict[str, Any]
    def get_configuration_history(self) -> List[Dict[str, Any]]
    
    # Change management
    def add_change_callback(self, callback: Callable[[str, Any, Any], None])
    def remove_change_callback(self, callback: Callable[[str, Any, Any], None])

# Global functions
def get_configuration_manager(config_file: Optional[str] = None) -> ConfigurationManager
def get_config() -> ConfigurationSchema
def get_config_value(key: str, default: Any = None) -> Any
def set_config_value(key: str, value: Any)
```

**Example Usage:**

```python
# Get configuration manager
config_manager = get_configuration_manager()

# Access configuration values
server_port = config_manager.get_value("server_port")
worker_limits = config_manager.get_value("max_workers_per_type")

# Update configuration
config_manager.set_value("server_port", 9000)
config_manager.set_value("max_workers_per_type.EXECUTOR", 30)

# Save configuration
config_manager.save_to_file("my_config.json")

# Add change callback
def on_config_change(key, old_value, new_value):
    print(f"Configuration changed: {key} = {new_value}")

config_manager.add_change_callback(on_config_change)
```

## Plugin System

### PluginManager

Plugin lifecycle and management.

```python
from botted_library.core.plugin_system import PluginManager, IPlugin

class PluginManager:
    # Plugin loading
    async def load_plugin(self, plugin_path: str) -> bool
    async def load_plugins_from_directory(self, directory: str) -> List[str]
    async def unload_plugin(self, plugin_name: str) -> bool
    
    # Plugin management
    def get_loaded_plugins(self) -> List[str]
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]
    async def enable_plugin(self, plugin_name: str) -> bool
    async def disable_plugin(self, plugin_name: str) -> bool
    
    # Plugin execution
    async def execute_plugin(self, plugin_name: str, method: str, parameters: Dict[str, Any]) -> Any
    def get_plugin_capabilities(self, plugin_name: str) -> List[str]

# Global functions
def get_plugin_manager() -> PluginManager
def get_plugin_registry() -> PluginRegistry
def get_plugin_discovery() -> PluginDiscovery
```

### IPlugin

Plugin interface for custom plugins.

```python
from botted_library.core.plugin_system import IPlugin

class IPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str
    
    @property
    @abstractmethod
    def version(self) -> str
    
    @property
    @abstractmethod
    def description(self) -> str
    
    @abstractmethod
    async def initialize(self) -> bool
    
    @abstractmethod
    async def shutdown(self) -> bool
    
    @abstractmethod
    def get_capabilities(self) -> List[str]
    
    @abstractmethod
    async def execute(self, capability: str, parameters: Dict[str, Any]) -> Any
```

**Example Plugin Implementation:**

```python
class WebScraperPlugin(IPlugin):
    @property
    def name(self) -> str:
        return "web_scraper"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Advanced web scraping capabilities"
    
    async def initialize(self) -> bool:
        # Initialize plugin resources
        return True
    
    async def shutdown(self) -> bool:
        # Clean up plugin resources
        return True
    
    def get_capabilities(self) -> List[str]:
        return ["scrape_url", "extract_data", "parse_html"]
    
    async def execute(self, capability: str, parameters: Dict[str, Any]) -> Any:
        if capability == "scrape_url":
            return await self._scrape_url(parameters["url"])
        # ... other capabilities
```

## Enhanced Tools

### EnhancedToolManager

Advanced tool management and execution.

```python
from botted_library.core.enhanced_tools import EnhancedToolManager, IEnhancedTool

class EnhancedToolManager:
    # Tool registration
    def register_tool(self, tool: IEnhancedTool) -> bool
    def unregister_tool(self, tool_name: str) -> bool
    def get_registered_tools(self) -> List[str]
    
    # Tool execution
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any
    async def execute_tool_with_timeout(self, tool_name: str, parameters: Dict[str, Any], timeout: int) -> Any
    
    # Tool management
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]
    def get_tool_capabilities(self, tool_name: str) -> List[str]
    def set_timeout(self, timeout: int)
    def set_max_concurrent(self, max_concurrent: int)
    
    # Performance optimization
    async def optimize_tool_execution(self, tool_name: str, parameters: Dict[str, Any]) -> Any
    def get_tool_performance_metrics(self, tool_name: str) -> Dict[str, Any]

# Global functions
def get_enhanced_tool_manager() -> EnhancedToolManager
```

### IEnhancedTool

Interface for enhanced tools.

```python
from botted_library.core.enhanced_tools import IEnhancedTool

class IEnhancedTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str
    
    @property
    @abstractmethod
    def description(self) -> str
    
    @property
    @abstractmethod
    def version(self) -> str
    
    @abstractmethod
    def get_capabilities(self) -> List[str]
    
    @abstractmethod
    async def execute(self, capability: str, parameters: Dict[str, Any]) -> Any
    
    @abstractmethod
    def validate_parameters(self, capability: str, parameters: Dict[str, Any]) -> bool
    
    @abstractmethod
    def get_parameter_schema(self, capability: str) -> Dict[str, Any]
```

**Example Tool Implementation:**

```python
class DataAnalysisTool(IEnhancedTool):
    @property
    def name(self) -> str:
        return "data_analysis"
    
    @property
    def description(self) -> str:
        return "Advanced data analysis and visualization"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    def get_capabilities(self) -> List[str]:
        return ["analyze_dataset", "create_visualization", "statistical_summary"]
    
    async def execute(self, capability: str, parameters: Dict[str, Any]) -> Any:
        if capability == "analyze_dataset":
            return await self._analyze_dataset(parameters["data"])
        # ... other capabilities
    
    def validate_parameters(self, capability: str, parameters: Dict[str, Any]) -> bool:
        # Validate parameters for the capability
        return True
    
    def get_parameter_schema(self, capability: str) -> Dict[str, Any]:
        # Return JSON schema for parameters
        return {"type": "object", "properties": {...}}
```

## Error Handling

### ErrorRecoverySystem

Comprehensive error handling and recovery.

```python
from botted_library.core.error_recovery import ErrorRecoverySystem

class ErrorRecoverySystem:
    def __init__(self, max_retry_attempts: int = 3, retry_delay: float = 1.0, enabled: bool = True)
    
    # Error handling
    async def handle_error(self, error_type: str, context: Dict[str, Any]) -> Dict[str, Any]
    async def retry_operation(self, operation: Callable, max_attempts: int = None) -> Any
    
    # Recovery strategies
    async def apply_recovery_strategy(self, error_type: str, context: Dict[str, Any]) -> bool
    def register_recovery_strategy(self, error_type: str, strategy: Callable)
    
    # Error analysis
    def analyze_error_patterns(self) -> Dict[str, Any]
    def get_error_statistics(self) -> Dict[str, Any]
    
    # Configuration
    def set_retry_policy(self, error_type: str, max_attempts: int, delay: float)
    def enable_recovery_for_error_type(self, error_type: str, enabled: bool)
```

## Monitoring

### MonitoringSystem

System performance and health monitoring.

```python
from botted_library.core.monitoring_system import MonitoringSystem

class MonitoringSystem:
    def __init__(self, enabled: bool = True, monitoring_interval: int = 30)
    
    # Metrics collection
    def collect_metrics(self) -> Dict[str, Any]
    def get_current_metrics(self) -> Dict[str, Any]
    def get_historical_metrics(self, time_range: str) -> List[Dict[str, Any]]
    
    # Health monitoring
    def get_system_health(self) -> Dict[str, Any]
    def check_component_health(self, component_name: str) -> Dict[str, Any]
    
    # Alerting
    def set_alert_threshold(self, metric_name: str, threshold: float, alert_type: str)
    def get_active_alerts(self) -> List[Dict[str, Any]]
    
    # Performance analysis
    def analyze_performance_trends(self) -> Dict[str, Any]
    def generate_performance_report(self) -> Dict[str, Any]
    
    # Configuration
    def set_monitoring_interval(self, interval: int)
    def enable_metric_collection(self, metric_name: str, enabled: bool)
```

## V1 Compatibility

### V1 Worker Interface

Backward compatibility with v1 workers.

```python
from botted_library.compatibility.v1_compatibility import create_worker, Worker

# V1 compatible functions
def create_worker(name: str, role: str, job_description: str) -> Worker

class Worker:
    def __init__(self, name: str, role: str, job_description: str)
    
    # V1 interface methods
    def call(self, task: str) -> str
    
    # Properties
    @property
    def name(self) -> str
    
    @property
    def role(self) -> str
    
    @property
    def job_description(self) -> str
```

**Example V1 Usage:**

```python
# Create V1 worker (backward compatible)
worker = create_worker("Sarah", "Marketing Manager", "Expert in market research")

# Use V1 interface
result = worker.call("Research our top 3 competitors")
print(result)

# V1 workers automatically get v2 collaborative features
```

### Migration Tools

Tools for migrating from v1 to v2.

```python
from botted_library.migration.migration_tools import MigrationTools

class MigrationTools:
    # Analysis
    def analyze_v1_usage(self, project_path: str) -> Dict[str, Any]
    def identify_migration_opportunities(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]
    
    # Migration planning
    def generate_migration_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]
    def estimate_migration_effort(self, migration_plan: Dict[str, Any]) -> Dict[str, Any]
    
    # Migration execution
    def apply_safe_migrations(self, project_path: str, migration_plan: Dict[str, Any]) -> Dict[str, Any]
    def generate_migration_code(self, migration_plan: Dict[str, Any]) -> str
    
    # Validation
    def validate_migration(self, project_path: str) -> Dict[str, Any]
    def test_backward_compatibility(self, project_path: str) -> Dict[str, Any]
```

## Global Functions

### System Management

```python
# System integration
from botted_library.core.system_integration import initialize_v2_system, shutdown_v2_system, get_system_integration

async def initialize_v2_system(config: Optional[SystemConfiguration] = None) -> SystemIntegration
async def shutdown_v2_system() -> bool
def get_system_integration(config: Optional[SystemConfiguration] = None) -> SystemIntegration

# Quick start
from botted_library.core.system_startup import quick_start_system

async def quick_start_system(config_file: Optional[str] = None) -> SystemIntegration
```

### Configuration

```python
# Configuration management
from botted_library.core.configuration_manager import get_config, get_config_value, set_config_value

def get_config() -> ConfigurationSchema
def get_config_value(key: str, default: Any = None) -> Any
def set_config_value(key: str, value: Any)
```

### Plugin and Tool Management

```python
# Plugin system
from botted_library.core.plugin_system import get_plugin_manager

def get_plugin_manager() -> PluginManager

# Enhanced tools
from botted_library.core.enhanced_tools import get_enhanced_tool_manager

def get_enhanced_tool_manager() -> EnhancedToolManager
```

## Error Codes and Exceptions

### Common Exceptions

```python
from botted_library.core.exceptions import (
    BottedLibraryError,
    WorkerError,
    CommunicationError,
    ConfigurationError,
    PluginError,
    ToolError
)

class BottedLibraryError(Exception):
    """Base exception for all Botted Library errors"""

class WorkerError(BottedLibraryError):
    """Worker-related errors"""

class CommunicationError(BottedLibraryError):
    """Communication and messaging errors"""

class ConfigurationError(BottedLibraryError):
    """Configuration-related errors"""

class PluginError(BottedLibraryError):
    """Plugin system errors"""

class ToolError(BottedLibraryError):
    """Enhanced tool errors"""
```

### Error Codes

| Code | Description | Category |
|------|-------------|----------|
| 1001 | Worker initialization failed | Worker |
| 1002 | Worker communication timeout | Communication |
| 1003 | Invalid worker type | Worker |
| 2001 | Server connection failed | Communication |
| 2002 | Message routing failed | Communication |
| 2003 | Collaborative space not found | Collaboration |
| 3001 | Configuration validation failed | Configuration |
| 3002 | Invalid configuration value | Configuration |
| 4001 | Plugin loading failed | Plugin |
| 4002 | Plugin execution error | Plugin |
| 5001 | Tool execution failed | Tool |
| 5002 | Tool timeout | Tool |

This API reference provides comprehensive documentation for all public interfaces in Botted Library v2. For more detailed examples and use cases, refer to the main README.md and the test files in the `tests/` directory.
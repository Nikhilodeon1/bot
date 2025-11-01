# Botted Library v2 - Collaborative AI Workers

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](tests/)

**Transform your AI workflows with collaborative, intelligent workers that communicate and coordinate through a powerful background server.**

## 🌟 What's New in v2

Botted Library v2 introduces a revolutionary collaborative architecture where AI workers operate like a coordinated team in a virtual office environment:

- **🏢 Background Server Architecture**: Automatic server deployment handles all operations behind the scenes
- **🤝 Worker Communication**: Workers communicate with each other through the server for coordinated task execution
- **🎯 Specialized Worker Types**: Three distinct worker roles - Planners, Executors, and Verifiers
- **🚀 Collaborative Spaces**: Shared workspaces with whiteboards, file systems, and real-time collaboration
- **🧠 Intelligent Planning**: Planners create and manage other workers dynamically based on objectives
- **⚡ Dual Modes**: Manual control or fully autonomous operation
- **🔧 Enhanced Integrations**: Extensive plugin system and advanced tool integrations
- **🔄 Full v1 Compatibility**: Seamless upgrade path from existing v1 implementations

## 🚀 Quick Start

### Installation

```bash
pip install botted-library
```

### V1 Compatibility (Existing Users)

Your existing v1 code continues to work unchanged:

```python
from botted_library import create_worker

# Your existing v1 code works exactly the same
worker = create_worker("Sarah", "Marketing Manager", "Expert in market research")
result = worker.call("Research our top 3 competitors")
print(result)
```

### V2 Collaborative Features

#### Quick System Start

```python
from botted_library import quick_start_system
import asyncio

async def main():
    # Start the collaborative system
    system = await quick_start_system()
    print("🤖 Collaborative AI system is ready!")

asyncio.run(main())
```

#### Manual Mode - Direct Control

```python
from botted_library.core.mode_manager import ModeManager
from botted_library.core.interfaces import WorkerType

# Initialize system in manual mode
mode_manager = ModeManager()
await mode_manager.switch_to_manual_mode()

# Create specialized workers
planner = await mode_manager.create_worker(WorkerType.PLANNER, "Strategic Planner")
executor = await mode_manager.create_worker(WorkerType.EXECUTOR, "Data Analyst")
verifier = await mode_manager.create_worker(WorkerType.VERIFIER, "Quality Controller")

# Create collaborative space
space = await mode_manager.create_collaborative_space("Market Research Project")
await space.add_participants([planner.worker_id, executor.worker_id, verifier.worker_id])

# Execute coordinated workflow
strategy = await planner.create_strategy("Comprehensive market analysis")
task = await planner.assign_task_to_executor(executor.worker_id, strategy.tasks[0])
result = await executor.execute_task(task)
validation = await verifier.validate_output(result)

if validation.approved:
    print("✅ Task completed and verified!")
```

#### Auto Mode - Autonomous Operation

```python
from botted_library.core.mode_manager import ModeManager

# Initialize system in auto mode
mode_manager = ModeManager()
await mode_manager.switch_to_auto_mode()

# Define objective and let the system handle everything
objective = """
Create a comprehensive business plan for a sustainable energy startup, 
including market analysis, financial projections, and go-to-market strategy.
"""

# The system automatically:
# 1. Creates an initial planner
# 2. Planner designs the optimal team structure
# 3. Creates necessary executors and verifiers
# 4. Coordinates the entire workflow
# 5. Delivers validated results

result = await mode_manager.execute_objective(objective)
print(f"🎯 Objective completed: {result.summary}")
```

## 🏗️ Architecture Overview

### The Office Building Metaphor

Think of Botted Library v2 as a virtual office building where AI workers collaborate:

```
┌─────────────────────────────────────────┐
│             🏢 Office Building           │
│  ┌─────────────────────────────────────┐ │
│  │        📡 Communication Hub         │ │
│  │     (Background Server)             │ │
│  └─────────────────────────────────────┘ │
│                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ 🧠      │ │ ⚡      │ │ ✅      │   │
│  │Planners │ │Executors│ │Verifiers│   │
│  │         │ │         │ │         │   │
│  └─────────┘ └─────────┘ └─────────┘   │
│                                         │
│  ┌─────────────────────────────────────┐ │
│  │     🤝 Collaborative Spaces         │ │
│  │  • Shared Whiteboards               │ │
│  │  • File Systems                     │ │
│  │  • Real-time Communication         │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Worker Types

#### 🧠 Planners
- **Role**: Strategic thinking and coordination
- **Capabilities**:
  - Create execution strategies
  - Design team structures
  - Assign tasks to executors
  - Monitor progress and adapt plans
  - Create new workers as needed

#### ⚡ Executors
- **Role**: Task execution and action
- **Capabilities**:
  - Perform assigned tasks
  - Use tools and integrations
  - Report progress to planners
  - Collaborate with other executors

#### ✅ Verifiers
- **Role**: Quality assurance and validation
- **Capabilities**:
  - Validate output quality
  - Check accuracy and completeness
  - Approve deliverables
  - Provide feedback for improvements

### Collaborative Spaces

Workers can collaborate in shared spaces that include:

- **📝 Shared Whiteboards**: Visual collaboration and planning
- **📁 File Systems**: Shared document access and version control
- **💬 Real-time Communication**: Direct worker-to-worker messaging
- **📊 Progress Tracking**: Shared visibility into project status

## 🔧 Configuration

### Environment-Specific Configurations

Botted Library v2 includes pre-configured settings for different environments:

#### Development
```python
from botted_library.core.system_startup import create_development_startup

startup = create_development_startup()
system = await startup.start_system()
```

#### Production
```python
from botted_library.core.system_startup import create_production_startup

startup = create_production_startup()
system = await startup.start_system()
```

### Custom Configuration

```python
from botted_library.core.system_integration import SystemConfiguration
from botted_library.core.interfaces import WorkerType

config = SystemConfiguration(
    server_host="localhost",
    server_port=8765,
    max_workers_per_type={
        WorkerType.PLANNER: 5,
        WorkerType.EXECUTOR: 20,
        WorkerType.VERIFIER: 10
    },
    enable_monitoring=True,
    enable_error_recovery=True,
    plugin_directories=["./plugins", "~/.botted_library/plugins"]
)

system = SystemIntegration(config)
await system.initialize_system()
```

### Environment Variables

Configure the system using environment variables:

```bash
# Server Configuration
export BOTTED_SERVER_HOST=localhost
export BOTTED_SERVER_PORT=8765
export BOTTED_MAX_CONNECTIONS=100

# Worker Configuration
export BOTTED_MAX_PLANNERS=5
export BOTTED_MAX_EXECUTORS=20
export BOTTED_MAX_VERIFIERS=10

# Features
export BOTTED_ENABLE_MONITORING=true
export BOTTED_ENABLE_ERROR_RECOVERY=true
export BOTTED_AUTO_LOAD_PLUGINS=true

# Logging
export BOTTED_LOG_LEVEL=INFO
export BOTTED_LOG_FILE=/var/log/botted_library.log
```

## 🔌 Plugin System

Extend functionality with plugins:

```python
from botted_library.core.plugin_system import get_plugin_manager

plugin_manager = get_plugin_manager()

# Load plugins from directory
await plugin_manager.load_plugins_from_directory("./my_plugins")

# Enable specific plugin
await plugin_manager.enable_plugin("advanced_web_scraper")

# Create custom plugin
class MyCustomPlugin:
    def __init__(self):
        self.name = "my_custom_plugin"
    
    async def execute(self, parameters):
        # Plugin implementation
        return {"result": "success"}

# Register plugin
plugin_manager.register_plugin(MyCustomPlugin())
```

## 🛠️ Enhanced Tools

Workers have access to enhanced tools:

```python
from botted_library.core.enhanced_tools import get_enhanced_tool_manager

tool_manager = get_enhanced_tool_manager()

# Register custom tool
@tool_manager.register_tool("data_analyzer")
async def analyze_data(data, analysis_type="basic"):
    # Tool implementation
    return {"analysis": "completed", "insights": [...]}

# Use tool in worker
result = await executor.use_tool("data_analyzer", {
    "data": dataset,
    "analysis_type": "advanced"
})
```

## 📊 Monitoring and Error Recovery

### Built-in Monitoring

```python
from botted_library.core.monitoring_system import MonitoringSystem

monitoring = MonitoringSystem(enabled=True, monitoring_interval=30)
await monitoring.initialize()

# Get system metrics
metrics = monitoring.get_current_metrics()
print(f"Active workers: {metrics['active_workers']}")
print(f"System health: {metrics['system_health']}")
```

### Error Recovery

```python
from botted_library.core.error_recovery import ErrorRecoverySystem

error_recovery = ErrorRecoverySystem(
    max_retry_attempts=3,
    retry_delay=1.0,
    enabled=True
)

# Automatic error handling and recovery
await error_recovery.handle_error("worker_timeout", {
    "worker_id": "executor_1",
    "task_id": "task_123"
})
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_comprehensive_features.py -v
python -m pytest tests/test_system_integration.py -v
python -m pytest tests/test_requirements_validation.py -v

# Run system validation
python validate_system.py
```

## 📚 Migration from v1

### Automatic Migration

Existing v1 code works without changes. For enhanced features:

```python
from botted_library.migration.migration_tools import MigrationTools

migration = MigrationTools()

# Analyze existing v1 usage
analysis = migration.analyze_v1_usage("./my_project")

# Generate migration recommendations
recommendations = migration.generate_migration_plan(analysis)

# Apply automatic migrations where possible
migration.apply_safe_migrations("./my_project", recommendations)
```

### Manual Migration Guide

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed migration instructions.

## 🎯 Use Cases

### Business Analysis
```python
# Auto mode: Complete business analysis
objective = "Analyze market opportunities for AI-powered customer service tools"
result = await mode_manager.execute_objective(objective)
```

### Content Creation
```python
# Manual mode: Coordinated content creation
planner = await create_planner("Content Strategy Lead")
writers = await create_executors(["Blog Writer", "Social Media Specialist"], count=2)
editor = await create_verifier("Content Editor")

# Collaborative workflow
strategy = await planner.create_content_strategy("AI trends blog series")
articles = await writers.execute_parallel(strategy.article_tasks)
final_content = await editor.review_and_approve(articles)
```

### Research Projects
```python
# Auto mode: Comprehensive research
research_objective = """
Conduct comprehensive research on renewable energy market trends,
including technology analysis, market sizing, and competitive landscape.
"""

research_results = await mode_manager.execute_objective(research_objective)
```

## 🔒 Security and Privacy

- **Secure Communication**: All worker communication is encrypted
- **Access Control**: Role-based access to collaborative spaces
- **Data Privacy**: Local processing with optional cloud integrations
- **Audit Logging**: Complete audit trail of all worker actions

## 🚀 Performance

- **Scalable Architecture**: Handles hundreds of concurrent workers
- **Efficient Resource Management**: Automatic cleanup and optimization
- **Load Balancing**: Intelligent task distribution across workers
- **Caching**: Smart caching for improved performance

## 📖 API Reference

### Core Classes

- **SystemIntegration**: Main system coordinator
- **SystemStartup**: System initialization and configuration
- **ModeManager**: Manual/Auto mode management
- **CollaborativeServer**: Background server for worker communication
- **EnhancedWorkerRegistry**: Worker lifecycle management
- **ConfigurationManager**: System configuration and settings

### Worker Classes

- **PlannerWorker**: Strategic planning and coordination
- **ExecutorWorker**: Task execution and action
- **VerifierWorker**: Quality assurance and validation

### Collaborative Features

- **CollaborativeSpace**: Shared workspace for teams
- **SharedWhiteboard**: Visual collaboration tool
- **SharedFileSystem**: Shared file access and version control

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/botted-library/botted-library.git
cd botted-library

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Run validation
python validate_system.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Full documentation](https://botted-library.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/botted-library/botted-library/issues)
- **Discussions**: [GitHub Discussions](https://github.com/botted-library/botted-library/discussions)
- **Email**: support@botted-library.com

## 🗺️ Roadmap

### v2.1 (Coming Soon)
- Advanced AI model integrations
- Enhanced plugin marketplace
- Real-time collaboration UI
- Performance optimizations

### v2.2 (Future)
- Multi-language support
- Cloud deployment options
- Advanced analytics dashboard
- Enterprise features

---

**Ready to transform your AI workflows? Start with Botted Library v2 today!** 🚀

```python
from botted_library import quick_start_system
import asyncio

async def main():
    system = await quick_start_system()
    print("🤖 Welcome to the future of collaborative AI!")

asyncio.run(main())
```
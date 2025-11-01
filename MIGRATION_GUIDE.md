# Botted Library v1 to v2 Migration Guide

## Overview

Botted Library v2 introduces powerful collaborative features while maintaining **100% backward compatibility** with v1 code. Your existing workers can now communicate, delegate tasks, and work together in shared spaces - all without changing a single line of your existing code!

## 🚀 Quick Start (Zero Code Changes)

Your existing v1 code works immediately in v2 with collaborative features automatically enabled:

```python
# Your existing v1 code - works unchanged in v2!
from botted_library import create_worker

sarah = create_worker(
    name="Sarah",
    role="Marketing Manager", 
    job_description="Expert in market research and competitive analysis"
)

# This now automatically includes collaborative features
result = sarah.call("Research our top 3 competitors")
```

**What's new:** Sarah can now collaborate with other workers, access shared resources, and benefit from automatic load balancing - all transparently!

## 🆕 New Collaborative Features

### 1. Worker Communication & Delegation

```python
# Create multiple workers
researcher = create_worker("Alice", "Researcher", "Data analysis expert")
writer = create_worker("Bob", "Writer", "Content creation specialist")

# Workers can now delegate tasks to each other
research_result = researcher.call("Analyze market trends for Q4")

# Alice can delegate writing to Bob
summary = researcher.delegate_task(
    "Write an executive summary of this research",
    preferred_role="Writer"
)
```

### 2. Shared Resources

```python
# Workers automatically have access to shared resources
worker1 = create_worker("Designer", "UI Designer", "Interface design expert")
worker2 = create_worker("Developer", "Frontend Dev", "React specialist")

# Both can access shared whiteboards and files
design = worker1.call("Create a wireframe for the login page")
implementation = worker2.call("Implement the login page based on shared design")
```

### 3. Automatic Collaboration

```python
# Workers automatically collaborate when beneficial
complex_task = "Build a complete user authentication system with security audit"

# The worker will automatically:
# 1. Break down the task
# 2. Delegate parts to appropriate specialists
# 3. Coordinate the work
# 4. Provide integrated results
result = developer.call(complex_task)
```

## 📋 Migration Steps

### Step 1: Verify Compatibility (5 minutes)

1. **Run your existing code** - it should work unchanged
2. **Look for collaborative messages** - you'll see notifications about collaborative features
3. **Check worker status** - verify collaborative features are enabled

```python
# Check if collaborative features are working
from botted_library.compatibility import get_compatibility_status

status = get_compatibility_status()
print(f"Collaborative features: {status['collaborative_enabled']}")
print(f"Active workers: {status['v1_workers_count']}")
```

### Step 2: Explore New Capabilities (15 minutes)

```python
# Try worker delegation
worker1 = create_worker("Analyst", "Data Analyst", "Statistical analysis")
worker2 = create_worker("Visualizer", "Data Viz", "Chart and graph creation")

# Analyst delegates visualization to specialist
analysis = worker1.call("Analyze sales data trends")
charts = worker1.delegate_task(
    "Create visualizations for this analysis", 
    preferred_role="Data Viz"
)
```

### Step 3: Optimize Workflows (30 minutes)

```python
# Design collaborative workflows
planner = create_worker("Planner", "Project Manager", "Strategic planning")
executor = create_worker("Executor", "Developer", "Implementation specialist") 
verifier = create_worker("Verifier", "QA Engineer", "Quality assurance")

# Collaborative workflow
plan = planner.call("Create development plan for user authentication")
code = executor.call(f"Implement: {plan['summary']}")
review = verifier.call(f"Review and test: {code['deliverables']}")
```

### Step 4: Advanced Configuration (Optional)

```python
# Custom server configuration (if needed)
from botted_library.core.collaborative_server import ServerConfig
from botted_library.compatibility import enable_collaborative_features

# Configure collaborative server
config = ServerConfig(
    max_workers=50,
    auto_cleanup=True,
    log_level="INFO"
)

enable_collaborative_features()
```

## 🔧 Migration Tools

### Automated Analysis

```python
from botted_library.migration import MigrationAnalyzer, create_migration_report

# Analyze your project for migration opportunities
analyzer = MigrationAnalyzer()
report = analyzer.analyze_project("/path/to/your/project")

print(f"Compatibility Score: {report.compatibility_score}/1.0")
print(f"Migration Time: {report.estimated_migration_time}")

# Generate detailed report
create_migration_report("/path/to/project", "migration_report.md")
```

### Interactive Migration Guide

```python
from botted_library.migration import print_migration_steps, check_migration_readiness

# Check if environment is ready
check_migration_readiness()

# Get step-by-step guide
print_migration_steps()
```

## 🎯 Worker Specialization

V2 introduces three specialized worker types for complex workflows:

### Planner Workers
- Create strategies and execution plans
- Manage other workers
- Coordinate complex projects

### Executor Workers  
- Perform tasks and actions
- Use tools and integrations
- Execute plans from planners

### Verifier Workers
- Validate work quality
- Provide feedback and improvements
- Ensure output standards

```python
# Specialized workers (v2 native)
from botted_library.core.enhanced_worker import EnhancedWorker
from botted_library.core.enhanced_worker_registry import WorkerType

planner = EnhancedWorker("Alice", "Strategic Planner", WorkerType.PLANNER)
executor = EnhancedWorker("Bob", "Task Executor", WorkerType.EXECUTOR)
verifier = EnhancedWorker("Carol", "Quality Checker", WorkerType.VERIFIER)
```

## 🔍 Troubleshooting

### Common Issues

**Workers not collaborating?**
```python
# Check server status
from botted_library.compatibility import get_compatibility_status
status = get_compatibility_status()

if not status['collaborative_enabled']:
    from botted_library.compatibility import enable_collaborative_features
    enable_collaborative_features()
```

**Import errors?**
```python
# Use main import (recommended)
from botted_library import create_worker  # ✅ Good

# Avoid direct imports
from botted_library.simple_worker import create_worker  # ⚠️ Not recommended
```

**Performance issues?**
```python
# Adjust server configuration
from botted_library.core.collaborative_server import ServerConfig

config = ServerConfig(
    max_workers=25,  # Reduce if needed
    auto_cleanup=True
)
```

## 💡 Best Practices

1. **Start Simple**: Keep existing v1 code unchanged initially
2. **Gradual Adoption**: Introduce collaborative features incrementally  
3. **Worker Specialization**: Use different worker types for complex workflows
4. **Monitor Performance**: Check collaborative interactions and optimize
5. **Test Thoroughly**: Validate collaborative features in development first

## 🆚 V1 vs V2 Comparison

| Feature | V1 | V2 |
|---------|----|----|
| Worker Creation | ✅ `create_worker()` | ✅ Same + collaborative |
| Task Execution | ✅ `worker.call()` | ✅ Same + collaboration context |
| Worker Communication | ❌ None | ✅ Automatic delegation |
| Shared Resources | ❌ None | ✅ Whiteboards, files |
| Load Balancing | ❌ Manual | ✅ Automatic |
| Worker Types | ❌ Generic | ✅ Specialized (Planner/Executor/Verifier) |
| Server Management | ❌ None | ✅ Background server |
| Backward Compatibility | N/A | ✅ 100% compatible |

## 🎉 Success Indicators

You'll know migration is successful when you see:

- ✅ Existing v1 code runs without changes
- ✅ Workers show collaborative features messages
- ✅ Multiple workers can communicate and delegate
- ✅ Shared resources are accessible
- ✅ Performance is maintained or improved

## 📚 Additional Resources

- **API Documentation**: Full v2 API reference
- **Examples Repository**: Sample collaborative workflows
- **Community Forum**: Get help from other users
- **Migration Support**: Professional migration assistance

## 🆘 Getting Help

```python
# Built-in help
from botted_library.migration import print_migration_steps
print_migration_steps()

# Check compatibility
from botted_library.compatibility import get_compatibility_status
print(get_compatibility_status())

# Analyze your project
from botted_library.migration import create_migration_report
create_migration_report("/your/project/path", "report.md")
```

---

**Ready to migrate?** Your v1 code already works in v2! Just import and run - collaborative features are automatically enabled. 🚀
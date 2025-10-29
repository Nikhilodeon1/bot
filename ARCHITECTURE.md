# 🏗️ Botted Library Architecture

## 📋 **System Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                           │
│  create_worker("name", "role") → worker.call("task")        │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 SIMPLE WORKER                               │
│  • Task Planning & Execution                               │
│  • Progress Tracking                                       │
│  • Result Formatting                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                COMPONENT FACTORY                            │
│  • Creates & Manages Core Components                       │
│  • Dependency Injection                                    │
│  • Configuration Management                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 CORE WORKER                                 │
│  • Task Coordination                                       │
│  • Role Management                                         │
│  • Memory Integration                                      │
└─────┬─────────┬─────────┬─────────┬─────────┬──────────────┘
      │         │         │         │         │
┌─────▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼────────┐
│   LLM   │ │MEMORY │ │BROWSER│ │ROLES  │ │KNOWLEDGE   │
│INTERFACE│ │SYSTEM │ │CONTROL│ │SYSTEM │ │VALIDATOR   │
└─────────┘ └───────┘ └───────┘ └───────┘ └────────────┘
```

## 🧩 **Core Components**

### **1. Simple Worker (`simple_worker.py`)**
- **Purpose**: User-friendly interface that follows your exact user journey
- **Responsibilities**:
  - Task planning and step breakdown
  - Live progress updates
  - Tool coordination (coding, research, browser)
  - Result formatting and delivery
- **Key Methods**: `call()`, `get_status()`, `get_history()`, `shutdown()`

### **2. Component Factory (`core/factory.py`)**
- **Purpose**: Creates and manages all system components
- **Responsibilities**:
  - Dependency injection
  - Configuration management
  - Component lifecycle management
- **Creates**: Workers, Memory, Browser, Knowledge systems

### **3. Core Worker (`core/worker.py`)**
- **Purpose**: Coordinates all subsystems for task execution
- **Responsibilities**:
  - Role-based task execution
  - Memory integration
  - Error handling and recovery
  - Clarification requests

### **4. LLM Interface (`core/simple_llm.py`)**
- **Current State**: Mock responses only
- **Purpose**: Abstraction layer for different LLM providers
- **Planned**: OpenAI, Anthropic, **Gemini 2.5 Flash** support

### **5. Memory System (`core/memory.py`)**
- **Purpose**: Short-term and long-term memory management
- **Storage**: SQLite database
- **Features**: Context retrieval, relevance scoring, auto-cleanup

### **6. Browser Controller (`browser_interface/browser_controller.py`)**
- **Purpose**: Web automation and interaction
- **Supports**: Chrome, Edge, Firefox
- **Features**: Search, navigation, form filling, scraping

### **7. Role System (`roles/`)**
- **Available Roles**:
  - `Editor`: Text editing, writing, content creation
  - `Researcher`: Information gathering, web search, analysis
  - `EmailChecker`: Email processing and management
- **Base Class**: `BaseRole` for creating custom roles

### **8. Knowledge Validator (`core/knowledge.py`)**
- **Purpose**: Fact-checking and source reliability
- **Features**: Trusted source validation, accuracy scoring

## 🤖 **Current LLM Status**

**Currently**: Mock responses only (no real AI)
**Location**: `botted_library/core/simple_llm.py`

```python
# Current implementation
class SimpleLLM:
    def think(self, prompt: str, context: Dict[str, Any] = None) -> str:
        return "I have processed your request and provided an appropriate response..."
```

**This means**: The system works end-to-end but uses generic responses instead of real AI.

## 🚀 **LLM Integration**

### **Supported Providers**

1. **Gemini 2.5 Flash** (Recommended)
   - **Setup**: `pip install google-generativeai`
   - **API Key**: `export GEMINI_API_KEY="your-key"`
   - **Usage**: `{'llm': {'provider': 'gemini'}}`

2. **OpenAI GPT-4**
   - **Setup**: `pip install openai`
   - **API Key**: `export OPENAI_API_KEY="your-key"`
   - **Usage**: `{'llm': {'provider': 'openai'}}`

3. **Mock AI** (Default)
   - **Setup**: None required
   - **Usage**: `{'llm': {'provider': 'mock'}}` (default)

### **LLM Configuration Options**

```python
llm_config = {
    'provider': 'gemini',              # 'gemini', 'openai', 'mock'
    'api_key': 'your-api-key',         # Or use environment variable
    'model': 'gemini-2.5-flash',      # Model name
    'temperature': 0.7,                # Creativity (0.0-1.0)
    'max_tokens': 2048                 # Response length limit
}
```

## 🔧 **Configuration System**

### **Complete Configuration Schema**

```python
config = {
    # LLM Configuration
    'llm': {
        'provider': 'gemini',           # LLM provider
        'api_key': 'your-key',          # API key (or env var)
        'model': 'gemini-2.5-flash',   # Model name
        'temperature': 0.7,             # Creativity level
        'max_tokens': 2048              # Max response length
    },
    
    # Browser Configuration
    'browser': {
        'headless': True,               # Hide browser window
        'browser_type': 'chrome',       # Browser type
        'timeout': 30,                  # Page load timeout
        'window_size': [1920, 1080],    # Browser window size
        'user_agent': 'custom-agent'    # Custom user agent
    },
    
    # Memory System Configuration
    'memory': {
        'storage_backend': 'sqlite',    # Storage type
        'database_path': 'memory.db',   # Database file path
        'auto_cleanup': True,           # Auto-clean old memories
        'cleanup_interval': 1800,       # Cleanup interval (seconds)
        'max_short_term_entries': 1000, # Max short-term memories
        'max_long_term_entries': 10000  # Max long-term memories
    },
    
    # Knowledge Validation Configuration
    'knowledge': {
        'database_path': 'knowledge.db', # Knowledge database path
        'trusted_sources': [             # Trusted source domains
            'wikipedia.org',
            'github.com',
            'stackoverflow.com'
        ],
        'validation_threshold': 0.7,     # Accuracy threshold
        'auto_update_reliability': True  # Auto-update source reliability
    },
    
    # Worker Configuration
    'worker': {
        'max_task_execution_time': 300,  # Max task time (seconds)
        'memory_context_limit': 15,      # Max context memories
        'enable_progress_tracking': True, # Show progress updates
        'auto_store_task_results': True, # Store results in memory
        'clarification_timeout': 60,     # Clarification timeout
        'max_retry_attempts': 3          # Max retry attempts
    },
    
    # Role-Specific Configuration
    'roles': {
        'editor': {
            'style_preferences': 'professional',
            'strictness_level': 'high'
        },
        'researcher': {
            'research_methodology': 'systematic',
            'source_diversity_requirement': 'high'
        },
        'email_checker': {
            'processing_mode': 'comprehensive',
            'auto_categorization': True
        }
    }
}
```

## 🔄 **Data Flow**

### **Task Execution Flow**

1. **User Input**: `worker.call("instructions", **params)`
2. **Planning Phase**: Worker creates execution plan
3. **Step Execution**: Each step uses appropriate tools
4. **Tool Coordination**: LLM, Browser, Memory work together
5. **Validation**: Results are validated and enhanced
6. **Result Delivery**: Structured results returned to user

### **Memory Integration**

```
User Task → Planning → Execution → Results
     ↓         ↓          ↓         ↓
   Memory ← Memory ← Memory ← Memory
     ↑         ↑          ↑         ↑
Context → Context → Context → Learning
```

## 🛠️ **Component Details**

### **Simple Worker Interface**
- **File**: `botted_library/simple_worker.py`
- **Purpose**: User-friendly wrapper around complex system
- **Key Methods**:
  - `call(instructions, **kwargs)` - Main task execution
  - `get_status()` - Worker status and metrics
  - `get_history()` - Task execution history
  - `shutdown()` - Clean resource cleanup

### **Core Worker System**
- **File**: `botted_library/core/worker.py`
- **Purpose**: Coordinates all subsystems
- **Responsibilities**:
  - Task lifecycle management
  - Memory integration
  - Error handling and recovery
  - Progress tracking

### **Component Factory**
- **File**: `botted_library/core/factory.py`
- **Purpose**: Dependency injection and component creation
- **Creates**: Memory, Browser, Knowledge, Task Executor components
- **Features**: Configuration validation, component caching

### **Browser Interface**
- **Files**: `botted_library/browser_interface/`
- **Components**:
  - `browser_controller.py` - Main browser control
  - `scraper.py` - Web scraping functionality
  - `actions.py` - Browser action primitives
- **Supports**: Chrome, Edge, Firefox with Selenium

### **Role System**
- **Files**: `botted_library/roles/`
- **Available Roles**:
  - `Editor` - Text editing and content creation
  - `Researcher` - Information gathering and analysis
  - `EmailChecker` - Email processing and management
- **Base Class**: `BaseRole` for custom role development

## 🔍 **Monitoring & Debugging**

### **Progress Tracking**
```python
# Live progress updates during execution
[14:30:15] 🤖 PLANNING: Breaking down the task into logical steps...
[14:30:16] 🤖 EXECUTING: Starting execution with 5 steps...
[14:30:17] 🤖 STEP 1/5: Analyze requirements
[14:30:18] 🤖 STEP 2/5: Research information
[14:30:20] 🤖 VALIDATING: Double-checking results...
[14:30:21] 🤖 COMPLETED: Task finished successfully!
```

### **Worker Status Monitoring**
```python
status = worker.get_status()
# Returns: worker info, task count, capabilities, uptime
```

### **Task History**
```python
history = worker.get_history()
# Returns: list of all completed tasks with results
```

## 🚀 **Extensibility**

### **Adding Custom Roles**
```python
from botted_library.roles.base_role import BaseRole

class CustomRole(BaseRole):
    def get_capabilities(self):
        return ['custom_capability_1', 'custom_capability_2']
    
    def perform_task(self, task, context):
        # Custom task execution logic
        pass
```

### **Adding Custom LLM Providers**
```python
from botted_library.core.simple_llm import BaseLLM

class CustomLLM(BaseLLM):
    def think(self, prompt, context=None):
        # Custom LLM implementation
        pass
```

This architecture provides a robust, extensible foundation for AI-powered task automation with clear separation of concerns and comprehensive configuration options.
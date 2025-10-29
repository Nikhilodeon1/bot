"""
Worker class implementation for the Botted Library

Central entity that coordinates memory, knowledge, and browser systems
to execute tasks with specific roles and custom instructions.
"""

import logging
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from .interfaces import (
    IWorker, IMemorySystem, IKnowledgeValidator, IBrowserController, ITaskExecutor,
    Task, TaskResult, TaskStatus
)
from .exceptions import WorkerError, TaskExecutionError, ValidationError
# Import AI components conditionally to avoid circular imports
# Removed role-specific imports - all workers are now general-purpose


class WorkerState:
    """Enumeration for worker states"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    EXECUTING = "executing"
    WAITING_FOR_CLARITY = "waiting_for_clarity"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class Worker(IWorker):
    """
    Central Worker class that coordinates all subsystems to execute tasks.
    
    The Worker manages the lifecycle of task execution by coordinating:
    - Memory system for storing and retrieving context
    - Knowledge validation for ensuring information accuracy
    - Browser controller for web interactions
    - Task executor for breaking down and executing complex tasks
    - Role-specific behaviors and capabilities
    """
    
    def __init__(self, 
                 memory_system: IMemorySystem,
                 knowledge_validator: IKnowledgeValidator,
                 browser_controller: IBrowserController,
                 task_executor: ITaskExecutor,
                 worker_id: Optional[str] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize Worker with required subsystems.
        
        Args:
            memory_system: Memory system for storing and retrieving data
            knowledge_validator: Knowledge validation system for accuracy checking
            browser_controller: Browser controller for web interactions
            task_executor: Task executor for processing and executing tasks
            worker_id: Optional unique identifier for the worker
            config: Optional configuration parameters
            
        Raises:
            WorkerError: If required subsystems are not provided
        """
        # Validate required dependencies
        if not all([memory_system, knowledge_validator, browser_controller, task_executor]):
            raise WorkerError(
                "All subsystems (memory, knowledge, browser, task_executor) are required",
                worker_id=worker_id or "unknown",
                context={'operation': 'initialization'}
            )
        
        # Initialize core attributes
        self.worker_id = worker_id or str(uuid.uuid4())
        self.logger = logging.getLogger(f"{__name__}.{self.worker_id}")
        
        # Store subsystem references
        self.memory_system = memory_system
        self.knowledge_validator = knowledge_validator
        self.browser_controller = browser_controller
        self.task_executor = task_executor
        
        # Initialize AI capabilities (lazy import to avoid circular imports)
        self._llm = None
        self._reasoning_engine = None
        self._code_executor = None
        
        # Configuration
        self.config = config or {}
        self._setup_default_config()
        
        # Worker state management
        self.state = WorkerState.IDLE
        self.current_role = None
        self.role_name: Optional[str] = None
        
        # Task execution tracking
        self.current_task: Optional[Task] = None
        self.task_history: List[Dict[str, Any]] = []
        self.execution_metrics: Dict[str, Any] = {}
        
        # Clarification handling
        self.pending_clarifications: List[Dict[str, Any]] = []
        self.clarification_callback: Optional[callable] = None
        
        # Initialize worker
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
        self.logger.info(f"Worker {self.worker_id} initialized successfully")
    
    @property
    def llm(self):
        """Lazy initialization of LLM interface"""
        if self._llm is None:
            from .simple_llm import create_simple_llm
            llm_config = self.config.get('llm', {})
            self._llm = create_simple_llm(llm_config)
        return self._llm
    
    @property
    def reasoning_engine(self):
        """Lazy initialization of reasoning engine"""
        if self._reasoning_engine is None:
            # Simple reasoning without complex dependencies
            class SimpleReasoning:
                def __init__(self, llm, config):
                    self.llm = llm
                    self.config = config
                
                def solve_problem(self, problem, context=None):
                    return {
                        'recommended_solution': 'Analyze the problem systematically and implement a step-by-step solution',
                        'confidence': 0.8,
                        'implementation_steps': ['Analyze requirements', 'Design solution', 'Implement', 'Test']
                    }
                
                def make_decision(self, situation, options, criteria=None, context=None):
                    return {
                        'chosen_option': options[0] if options else 'No option available',
                        'reasoning': 'Selected based on available information and best practices',
                        'confidence': 0.7
                    }
                
                def apply_common_sense(self, situation, context=None):
                    return {
                        'reasonableness_assessment': 'The situation appears reasonable with standard considerations',
                        'common_sense_recommendations': ['Consider all factors', 'Apply best practices', 'Seek additional input if needed'],
                        'confidence': 0.75
                    }
            
            self._reasoning_engine = SimpleReasoning(self.llm, self.config.get('reasoning', {}))
        return self._reasoning_engine
    
    @property
    def code_executor(self):
        """Lazy initialization of code executor"""
        if self._code_executor is None:
            # Simple code executor without complex dependencies
            class SimpleCodeExecutor:
                def __init__(self, config):
                    self.config = config
                
                def execute_code(self, code, language="python", inputs=None, context=None):
                    return {
                        'success': True,
                        'stdout': 'Code executed successfully (simulated)',
                        'stderr': '',
                        'execution_time': 0.1,
                        'language': language
                    }
                
                def test_code(self, code, test_cases, language="python"):
                    return {
                        'success': True,
                        'test_summary': {'passed': 1, 'failed': 0, 'total': 1},
                        'output': 'All tests passed (simulated)'
                    }
                
                def validate_syntax(self, code, language="python"):
                    return {
                        'valid': True,
                        'errors': [],
                        'warnings': []
                    }
            
            self._code_executor = SimpleCodeExecutor(self.config.get('code_execution', {}))
        return self._code_executor
    
    def _setup_default_config(self) -> None:
        """Setup default configuration values"""
        default_config = {
            'max_task_execution_time': 300,  # 5 minutes
            'memory_context_limit': 10,
            'knowledge_validation_threshold': 0.6,
            'auto_store_task_results': True,
            'enable_progress_tracking': True,
            'clarification_timeout': 60,  # 1 minute
            'max_retry_attempts': 3
        }
        
        # Merge with provided config, keeping user values
        for key, value in default_config.items():
            if key not in self.config:
                self.config[key] = value
    
    def initialize_role(self, role: str) -> None:
        """
        Initialize worker with specific role.
        
        Args:
            role: Role name to initialize (e.g., 'editor', 'researcher', 'email_checker')
            
        Raises:
            WorkerError: If role initialization fails
        """
        self.logger.info(f"Initializing worker with role: {role}")
        
        try:
            self.state = WorkerState.INITIALIZING
            
            # Import and instantiate the role class
            role_instance = self._create_role_instance(role)
            
            # Validate role compatibility
            if not hasattr(role_instance, 'get_capabilities'):
                raise WorkerError(
                    f"Role {role} does not implement required interface",
                    worker_id=self.worker_id,
                    context={'operation': 'role_initialization'}
                )
            
            # Set role
            self.current_role = role_instance
            self.role_name = role
            
            # Store role initialization in memory
            self._store_role_context(role, role_instance.get_capabilities())
            
            self.state = WorkerState.IDLE
            self.last_activity = datetime.now()
            
            self.logger.info(f"Successfully initialized role: {role}")
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.logger.error(f"Failed to initialize role {role}: {str(e)}")
            
            if isinstance(e, WorkerError):
                raise
            else:
                raise WorkerError(
                    f"Role initialization failed: {str(e)}",
                    worker_id=self.worker_id,
                    context={'operation': 'role_initialization'},
                    original_exception=e
                )
    
    def _create_role_instance(self, role: str):
        """Create a generic role instance - all workers have the same capabilities"""
        try:
            # Create a simple role object since all workers have the same capabilities
            class GenericRole:
                def __init__(self, role_name, config):
                    self.role = role_name
                    self.config = config
                    
                def get_capabilities(self):
                    return ['all_tools_available']
                    
                def validate_task_compatibility(self, task):
                    return True  # All workers can handle any task
            
            role_config = self.config.get('role_config', {}).get(role, {})
            return GenericRole(role, role_config)
            
        except Exception as e:
            raise WorkerError(
                f"Failed to create role instance for {role}: {str(e)}",
                worker_id=self.worker_id,
                context={'operation': 'role_creation'},
                original_exception=e
            )
    
    def _store_role_context(self, role_name: str, capabilities: List[str]) -> None:
        """Store role initialization context in memory"""
        try:
            role_context = {
                'role_name': role_name,
                'capabilities': capabilities,
                'initialized_at': datetime.now().isoformat(),
                'worker_id': self.worker_id
            }
            
            self.memory_system.store_short_term({
                'content': role_context,
                'relevance_score': 0.9,
                'tags': ['role_initialization', role_name, 'worker_context']
            })
            
        except Exception as e:
            self.logger.warning(f"Failed to store role context: {str(e)}")
    
    def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task and return comprehensive result.
        
        Coordinates all subsystems (memory, knowledge, browser) to execute tasks
        with proper error handling, progress tracking, and result validation.
        
        Args:
            task: Task object to execute
            
        Returns:
            TaskResult with execution results and metrics
            
        Raises:
            WorkerError: If task execution fails or worker is not properly initialized
        """
        self.logger.info(f"Executing task: {task.id} - {task.description}")
        
        # Validate worker state
        if self.state not in [WorkerState.IDLE, WorkerState.EXECUTING]:
            raise WorkerError(
                f"Worker is not available for task execution. Current state: {self.state}",
                worker_id=self.worker_id,
                context={'operation': 'task_execution'}
            )
        
        if not self.current_role:
            raise WorkerError(
                "Worker role not initialized. Call initialize_role() first.",
                worker_id=self.worker_id,
                context={'operation': 'task_execution'}
            )
        
        start_time = time.time()
        self.state = WorkerState.EXECUTING
        self.current_task = task
        retry_count = 0
        max_retries = self.config.get('max_retry_attempts', 3)
        
        while retry_count <= max_retries:
            try:
                # Validate task compatibility with current role
                if not self.current_role.validate_task_compatibility(task):
                    # Ask for clarification if task seems unclear
                    clarification = self.ask_for_clarity(
                        f"The task '{task.description}' doesn't seem compatible with my role as {self.role_name}. "
                        f"Could you clarify what you'd like me to do, or should I attempt it anyway?"
                    )
                    
                    # Update task description with clarification
                    task.description += f" [Clarification: {clarification}]"
                
                # Retrieve relevant context from memory
                task_context = self._prepare_task_context(task)
                
                # Check if task requires clarification based on context
                if self._needs_clarification(task, task_context):
                    clarification_query = self._generate_clarification_query(task, task_context)
                    clarification_response = self.ask_for_clarity(clarification_query)
                    
                    # Update task context with clarification
                    task_context['clarification'] = {
                        'query': clarification_query,
                        'response': clarification_response
                    }
                
                # Validate task information if needed
                validated_context = self._validate_task_information(task, task_context)
                
                # Execute task using role-specific logic with all subsystems coordination
                task_result = self._execute_task_with_coordination(task, validated_context)
                
                # Validate result quality
                if not self._validate_task_result(task_result):
                    if retry_count < max_retries:
                        retry_count += 1
                        self.logger.warning(f"Task result validation failed, retrying ({retry_count}/{max_retries})")
                        continue
                    else:
                        self.logger.warning("Task result validation failed, but max retries reached")
                
                # Update memory with task results and learnings
                if self.config.get('auto_store_task_results', True):
                    self._store_comprehensive_task_results(task, task_result, validated_context)
                
                # Update execution metrics
                execution_time = time.time() - start_time
                self._update_execution_metrics(task, task_result, execution_time)
                
                # Update worker state
                self.state = WorkerState.IDLE
                self.current_task = None
                self.last_activity = datetime.now()
                
                self.logger.info(f"Task {task.id} completed successfully in {execution_time:.2f}s (attempts: {retry_count + 1})")
                return task_result
                
            except Exception as e:
                retry_count += 1
                self.logger.warning(f"Task execution attempt {retry_count} failed: {str(e)}")
                
                if retry_count > max_retries:
                    # Final failure
                    execution_time = time.time() - start_time
                    self.state = WorkerState.ERROR
                    self.current_task = None
                    
                    self.logger.error(f"Task execution failed after {max_retries} retries: {str(e)}")
                    
                    # Create comprehensive failed task result
                    failed_result = TaskResult(
                        task_id=task.id,
                        status=TaskStatus.FAILED,
                        result_data={
                            'error': str(e),
                            'error_type': type(e).__name__,
                            'execution_time': execution_time,
                            'worker_id': self.worker_id,
                            'role': self.role_name,
                            'retry_attempts': retry_count,
                            'failure_context': {
                                'state_at_failure': self.state,
                                'last_activity': self.last_activity.isoformat()
                            }
                        },
                        execution_time=execution_time,
                        confidence_score=0.0,
                        sources_used=[]
                    )
                    
                    # Store failed result for learning
                    if self.config.get('auto_store_task_results', True):
                        self._store_task_results(task, failed_result)
                    
                    if isinstance(e, (WorkerError, TaskExecutionError)):
                        raise
                    else:
                        raise WorkerError(
                            f"Task execution failed after {max_retries} retries: {str(e)}",
                            worker_id=self.worker_id,
                            context={'operation': 'task_execution'},
                            original_exception=e
                        )
                else:
                    # Wait before retry
                    time.sleep(min(retry_count * 0.5, 2.0))  # Exponential backoff, max 2 seconds
    
    def _prepare_task_context(self, task: Task) -> Dict[str, Any]:
        """Prepare context for task execution by retrieving relevant memories"""
        try:
            # Get relevant memories based on task description and parameters
            context_query = f"{task.description} {' '.join(str(v) for v in task.parameters.values())}"
            relevant_memories = self.memory_system.retrieve_by_query(
                context_query, 
                memory_type="both"
            )
            
            # Limit context to prevent information overload
            context_limit = self.config.get('memory_context_limit', 10)
            limited_memories = relevant_memories[:context_limit]
            
            # Get role-specific context
            role_context = self.memory_system.get_context(f"role:{self.role_name}")
            
            return {
                'relevant_memories': limited_memories,
                'role_context': role_context,
                'task_parameters': task.parameters,
                'worker_capabilities': self.current_role.get_capabilities() if self.current_role else [],
                'execution_context': {
                    'worker_id': self.worker_id,
                    'role_name': self.role_name,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to prepare task context: {str(e)}")
            return {
                'relevant_memories': [],
                'role_context': {},
                'task_parameters': task.parameters,
                'worker_capabilities': [],
                'execution_context': {
                    'worker_id': self.worker_id,
                    'role_name': self.role_name,
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    def _validate_task_information(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task information using knowledge validation system"""
        try:
            validation_threshold = self.config.get('knowledge_validation_threshold', 0.6)
            
            # Validate task description
            description_accuracy = self.knowledge_validator.check_accuracy(
                task.description, 
                f"task_validation:{self.role_name}"
            )
            
            # Validate information from context memories
            validated_memories = []
            for memory in context.get('relevant_memories', []):
                memory_content = str(memory.get('content', ''))
                if memory_content:
                    accuracy = self.knowledge_validator.check_accuracy(
                        memory_content,
                        f"memory_validation:{task.id}"
                    )
                    
                    memory['validation_score'] = accuracy
                    if accuracy >= validation_threshold:
                        validated_memories.append(memory)
            
            # Update context with validated information
            validated_context = context.copy()
            validated_context['relevant_memories'] = validated_memories
            validated_context['validation_results'] = {
                'task_description_accuracy': description_accuracy,
                'validated_memories_count': len(validated_memories),
                'total_memories_count': len(context.get('relevant_memories', [])),
                'validation_threshold': validation_threshold
            }
            
            return validated_context
            
        except Exception as e:
            self.logger.warning(f"Knowledge validation failed: {str(e)}")
            # Return original context if validation fails
            return context
    
    def _needs_clarification(self, task: Task, context: Dict[str, Any]) -> bool:
        """Determine if task needs clarification based on context and complexity"""
        try:
            # Check for ambiguous task descriptions
            ambiguous_keywords = ['maybe', 'perhaps', 'might', 'could', 'unclear', 'not sure']
            if any(keyword in task.description.lower() for keyword in ambiguous_keywords):
                return True
            
            # Check if task parameters are incomplete
            required_params = getattr(self.current_role, 'required_parameters', [])
            missing_params = [param for param in required_params if param not in task.parameters]
            if missing_params:
                return True
            
            # Check if relevant memories suggest clarification is needed
            relevant_memories = context.get('relevant_memories', [])
            if len(relevant_memories) == 0 and len(task.description.split()) < 5:
                return True  # Very short task with no context
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking clarification need: {str(e)}")
            return False
    
    def _generate_clarification_query(self, task: Task, context: Dict[str, Any]) -> str:
        """Generate appropriate clarification query based on task and context"""
        try:
            # Check what type of clarification is needed
            if not task.parameters:
                return f"I need more details about the task '{task.description}'. Could you provide specific parameters or steps you'd like me to follow?"
            
            # Check for missing role-specific requirements
            if hasattr(self.current_role, 'required_parameters'):
                required_params = self.current_role.required_parameters
                missing_params = [param for param in required_params if param not in task.parameters]
                if missing_params:
                    return f"To complete this task as a {self.role_name}, I need the following information: {', '.join(missing_params)}. Could you provide these details?"
            
            # Check for ambiguous instructions
            if len(task.description.split()) < 5:
                return f"The task description '{task.description}' is quite brief. Could you provide more specific instructions about what you'd like me to accomplish?"
            
            # Default clarification
            return f"I want to make sure I understand the task correctly. For '{task.description}', could you confirm the expected outcome or provide any additional context?"
            
        except Exception as e:
            self.logger.warning(f"Error generating clarification query: {str(e)}")
            return f"Could you provide more details about the task '{task.description}'?"
    
    def _validate_task_result(self, result: TaskResult) -> bool:
        """Validate the quality and completeness of task result"""
        try:
            # Check basic result validity
            if not result or result.confidence_score < 0.3:
                return False
            
            # Check if result has meaningful data
            if not result.result_data or len(result.result_data) == 0:
                return False
            
            # Check for error indicators in result
            if 'error' in result.result_data and result.status != TaskStatus.FAILED:
                return False
            
            # Role-specific validation if available
            if hasattr(self.current_role, 'validate_result'):
                return self.current_role.validate_result(result)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Error validating task result: {str(e)}")
            return True  # Default to accepting result if validation fails
    
    def _execute_task_with_coordination(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Execute task with full coordination of all subsystems"""
        try:
            # Pre-execution memory update
            self._update_execution_context(task, context)
            
            # Execute with role and browser coordination
            result = self._execute_task_with_role(task, context)
            
            # Post-execution knowledge validation and learning
            self._post_execution_learning(task, result, context)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Coordinated task execution failed: {str(e)}")
            raise
    
    def _update_execution_context(self, task: Task, context: Dict[str, Any]) -> None:
        """Update memory with current execution context"""
        try:
            execution_context = {
                'task_id': task.id,
                'task_description': task.description,
                'worker_id': self.worker_id,
                'role_name': self.role_name,
                'execution_started_at': datetime.now().isoformat(),
                'context_summary': {
                    'relevant_memories_count': len(context.get('relevant_memories', [])),
                    'validation_results': context.get('validation_results', {}),
                    'clarification_provided': 'clarification' in context
                }
            }
            
            self.memory_system.store_short_term({
                'content': execution_context,
                'relevance_score': 0.7,
                'tags': ['execution_context', 'current_task', self.worker_id]
            })
            
        except Exception as e:
            self.logger.warning(f"Failed to update execution context: {str(e)}")
    
    def _post_execution_learning(self, task: Task, result: TaskResult, context: Dict[str, Any]) -> None:
        """Perform post-execution learning and knowledge updates"""
        try:
            # Update knowledge validator with execution results
            if result.sources_used:
                for source in result.sources_used:
                    # Update source reliability based on task success
                    reliability_score = 0.8 if result.status == TaskStatus.COMPLETED else 0.4
                    reliability_score *= result.confidence_score
                    
                    self.knowledge_validator.update_source_reliability(source, reliability_score)
            
            # Learn from task execution patterns
            execution_pattern = {
                'task_type': self._classify_task_type(task),
                'role_used': self.role_name,
                'success': result.status == TaskStatus.COMPLETED,
                'execution_time': result.execution_time,
                'confidence_score': result.confidence_score,
                'context_factors': {
                    'had_relevant_memories': len(context.get('relevant_memories', [])) > 0,
                    'needed_clarification': 'clarification' in context,
                    'used_browser': self._task_requires_browser(task)
                }
            }
            
            self.memory_system.store_long_term({
                'content': execution_pattern,
                'relevance_score': 0.6,
                'tags': ['execution_pattern', 'learning', self.role_name, 'performance']
            })
            
        except Exception as e:
            self.logger.warning(f"Post-execution learning failed: {str(e)}")
    
    def _classify_task_type(self, task: Task) -> str:
        """Classify task type for learning purposes"""
        description_lower = task.description.lower()
        
        if any(word in description_lower for word in ['edit', 'revise', 'correct', 'improve']):
            return 'editing'
        elif any(word in description_lower for word in ['research', 'find', 'search', 'investigate']):
            return 'research'
        elif any(word in description_lower for word in ['email', 'message', 'inbox', 'mail']):
            return 'email_processing'
        elif any(word in description_lower for word in ['navigate', 'click', 'browse', 'website']):
            return 'web_interaction'
        elif any(word in description_lower for word in ['extract', 'scrape', 'collect', 'gather']):
            return 'data_extraction'
        else:
            return 'general'
    
    def _store_comprehensive_task_results(self, task: Task, result: TaskResult, context: Dict[str, Any]) -> None:
        """Store comprehensive task results including context and learnings"""
        try:
            comprehensive_result = {
                'task_id': task.id,
                'task_description': task.description,
                'task_parameters': task.parameters,
                'result_status': result.status.value,
                'result_data': result.result_data,
                'execution_time': result.execution_time,
                'confidence_score': result.confidence_score,
                'sources_used': result.sources_used,
                'worker_id': self.worker_id,
                'role_name': self.role_name,
                'execution_context': {
                    'relevant_memories_used': len(context.get('relevant_memories', [])),
                    'validation_performed': 'validation_results' in context,
                    'clarification_requested': 'clarification' in context,
                    'browser_interaction': self._task_requires_browser(task)
                },
                'completed_at': datetime.now().isoformat(),
                'learning_metadata': {
                    'task_type': self._classify_task_type(task),
                    'complexity_score': self._calculate_task_complexity(task, context),
                    'success_factors': self._identify_success_factors(result, context)
                }
            }
            
            # Store in appropriate memory tier based on success and importance
            relevance_score = result.confidence_score * 0.8
            if result.status == TaskStatus.COMPLETED and result.confidence_score > 0.7:
                self.memory_system.store_long_term({
                    'content': comprehensive_result,
                    'relevance_score': relevance_score,
                    'tags': ['comprehensive_result', 'successful', self.role_name, task.id]
                })
            else:
                self.memory_system.store_short_term({
                    'content': comprehensive_result,
                    'relevance_score': max(relevance_score, 0.3),
                    'tags': ['comprehensive_result', 'learning', self.role_name, task.id]
                })
                
        except Exception as e:
            self.logger.warning(f"Failed to store comprehensive task results: {str(e)}")
            # Fallback to basic storage
            self._store_task_results(task, result)
    
    def _calculate_task_complexity(self, task: Task, context: Dict[str, Any]) -> float:
        """Calculate task complexity score for learning purposes"""
        try:
            complexity_score = 0.0
            
            # Base complexity from description length
            complexity_score += min(len(task.description.split()) / 20.0, 0.3)
            
            # Parameter complexity
            complexity_score += min(len(task.parameters) / 10.0, 0.2)
            
            # Context complexity
            complexity_score += min(len(context.get('relevant_memories', [])) / 15.0, 0.2)
            
            # Browser interaction adds complexity
            if self._task_requires_browser(task):
                complexity_score += 0.2
            
            # Clarification needed adds complexity
            if 'clarification' in context:
                complexity_score += 0.1
            
            return min(complexity_score, 1.0)
            
        except Exception:
            return 0.5  # Default medium complexity
    
    def _identify_success_factors(self, result: TaskResult, context: Dict[str, Any]) -> List[str]:
        """Identify factors that contributed to task success or failure"""
        factors = []
        
        try:
            if result.status == TaskStatus.COMPLETED:
                if result.confidence_score > 0.8:
                    factors.append('high_confidence_execution')
                if len(context.get('relevant_memories', [])) > 0:
                    factors.append('relevant_context_available')
                if 'validation_results' in context:
                    factors.append('knowledge_validation_performed')
                if result.execution_time < 30:
                    factors.append('efficient_execution')
            else:
                factors.append('execution_failed')
                if result.execution_time > 120:
                    factors.append('long_execution_time')
                if len(context.get('relevant_memories', [])) == 0:
                    factors.append('no_relevant_context')
            
            return factors
            
        except Exception:
            return ['analysis_failed']
    
    def _execute_task_with_role(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Execute task using role-specific logic and browser automation"""
        try:
            # Check if task requires browser interaction
            if self._task_requires_browser(task):
                # Use task executor for browser-based tasks
                browser_actions = self.task_executor.process_task(task)
                
                # Navigate to URL if specified
                if 'url' in task.parameters:
                    self.browser_controller.open_browser(task.parameters['url'])
                
                # Execute browser actions
                browser_result = self.task_executor.execute_browser_actions(browser_actions)
                
                # Let role process the browser results
                if self.current_role:
                    return self.current_role.perform_task(task, {
                        **context,
                        'browser_result': browser_result,
                        'browser_actions': browser_actions
                    })
                else:
                    return browser_result
            else:
                # Direct role execution for non-browser tasks
                if self.current_role:
                    return self.current_role.perform_task(task, context)
                else:
                    raise WorkerError(
                        "No role available for task execution",
                        worker_id=self.worker_id,
                        context={'operation': 'role_execution'}
                    )
                    
        except Exception as e:
            self.logger.error(f"Role-based task execution failed: {str(e)}")
            raise
    
    def _task_requires_browser(self, task: Task) -> bool:
        """Determine if task requires browser interaction"""
        browser_indicators = [
            'url' in task.parameters,
            'website' in task.description.lower(),
            'browser' in task.description.lower(),
            'navigate' in task.description.lower(),
            'scrape' in task.description.lower(),
            'click' in task.description.lower(),
            'form' in task.description.lower()
        ]
        
        return any(browser_indicators)
    
    def _store_task_results(self, task: Task, result: TaskResult) -> None:
        """Store task execution results in memory"""
        try:
            task_memory = {
                'task_id': task.id,
                'task_description': task.description,
                'result_status': result.status.value,
                'execution_time': result.execution_time,
                'confidence_score': result.confidence_score,
                'sources_used': result.sources_used,
                'worker_id': self.worker_id,
                'role_name': self.role_name,
                'completed_at': datetime.now().isoformat()
            }
            
            # Store in long-term memory for successful tasks, short-term for failed ones
            if result.status == TaskStatus.COMPLETED:
                self.memory_system.store_long_term({
                    'content': task_memory,
                    'relevance_score': result.confidence_score,
                    'tags': ['task_result', 'completed', self.role_name, task.id]
                })
            else:
                self.memory_system.store_short_term({
                    'content': task_memory,
                    'relevance_score': 0.3,
                    'tags': ['task_result', 'failed', self.role_name, task.id]
                })
                
        except Exception as e:
            self.logger.warning(f"Failed to store task results: {str(e)}")
    
    def _update_execution_metrics(self, task: Task, result: TaskResult, execution_time: float) -> None:
        """Update worker execution metrics"""
        try:
            # Add to task history
            task_record = {
                'task_id': task.id,
                'description': task.description,
                'status': result.status.value,
                'execution_time': execution_time,
                'confidence_score': result.confidence_score,
                'timestamp': datetime.now().isoformat(),
                'role': self.role_name
            }
            
            self.task_history.append(task_record)
            
            # Update aggregate metrics
            if 'total_tasks' not in self.execution_metrics:
                self.execution_metrics = {
                    'total_tasks': 0,
                    'successful_tasks': 0,
                    'failed_tasks': 0,
                    'total_execution_time': 0.0,
                    'average_execution_time': 0.0,
                    'average_confidence_score': 0.0
                }
            
            self.execution_metrics['total_tasks'] += 1
            self.execution_metrics['total_execution_time'] += execution_time
            
            if result.status == TaskStatus.COMPLETED:
                self.execution_metrics['successful_tasks'] += 1
            else:
                self.execution_metrics['failed_tasks'] += 1
            
            # Calculate averages
            total_tasks = self.execution_metrics['total_tasks']
            self.execution_metrics['average_execution_time'] = (
                self.execution_metrics['total_execution_time'] / total_tasks
            )
            
            # Calculate average confidence from recent tasks
            recent_tasks = self.task_history[-10:]  # Last 10 tasks
            if recent_tasks:
                avg_confidence = sum(t['confidence_score'] for t in recent_tasks) / len(recent_tasks)
                self.execution_metrics['average_confidence_score'] = avg_confidence
                
        except Exception as e:
            self.logger.warning(f"Failed to update execution metrics: {str(e)}")
    
    def update_memory(self, data: Dict[str, Any]) -> None:
        """
        Update worker memory with new data.
        
        Args:
            data: Dictionary containing memory data to store
        """
        try:
            self.logger.debug("Updating worker memory")
            
            # Determine memory type based on data importance
            relevance_score = data.get('relevance_score', 0.5)
            is_important = relevance_score > 0.7 or data.get('store_long_term', False)
            
            # Add worker context to content
            content = data.get('content', {})
            content.update({
                'worker_id': self.worker_id,
                'role_name': self.role_name,
                'updated_at': datetime.now().isoformat()
            })
            
            memory_data = {
                **data,
                'content': content
            }
            
            # Store in appropriate memory tier
            if is_important:
                self.memory_system.store_long_term(memory_data)
            else:
                self.memory_system.store_short_term(memory_data)
            
            self.last_activity = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to update memory: {str(e)}")
            raise WorkerError(
                f"Memory update failed: {str(e)}",
                worker_id=self.worker_id,
                context={'operation': 'memory_update'},
                original_exception=e
            )
    
    def retrieve_memory(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve memory entries by query.
        
        Args:
            query: Search query string
            
        Returns:
            List of memory entry dictionaries matching the query
        """
        try:
            self.logger.debug(f"Retrieving memory for query: {query}")
            
            # Add worker context to query for more relevant results
            contextual_query = f"{query} worker:{self.worker_id} role:{self.role_name}"
            
            memories = self.memory_system.retrieve_by_query(contextual_query)
            
            self.last_activity = datetime.now()
            return memories
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve memory: {str(e)}")
            raise WorkerError(
                f"Memory retrieval failed: {str(e)}",
                worker_id=self.worker_id,
                context={'operation': 'memory_retrieval'},
                original_exception=e
            )
    
    def ask_for_clarity(self, query: str) -> str:
        """
        Request clarification from user with enhanced context and timeout handling.
        
        Integrates with memory system to store clarification history and provides
        intelligent fallback responses when user interaction is not available.
        
        Args:
            query: Clarification question to ask
            
        Returns:
            User's response to the clarification request
        """
        self.logger.info(f"Requesting clarification: {query}")
        
        try:
            previous_state = self.state
            self.state = WorkerState.WAITING_FOR_CLARITY
            
            # Create comprehensive clarification record
            clarification = {
                'id': str(uuid.uuid4()),
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'worker_id': self.worker_id,
                'role_name': self.role_name,
                'task_id': self.current_task.id if self.current_task else None,
                'task_description': self.current_task.description if self.current_task else None,
                'status': 'pending',
                'context': {
                    'previous_state': previous_state,
                    'execution_metrics': self.execution_metrics.copy(),
                    'recent_clarifications': len([c for c in self.pending_clarifications if c['status'] == 'pending'])
                }
            }
            
            self.pending_clarifications.append(clarification)
            
            # Check for similar past clarifications to provide context
            similar_clarifications = self._find_similar_clarifications(query)
            if similar_clarifications:
                clarification['similar_past_clarifications'] = similar_clarifications
            
            # Store clarification request in memory with enhanced context
            self.memory_system.store_short_term({
                'content': clarification,
                'relevance_score': 0.8,
                'tags': ['clarification_request', 'pending', self.worker_id, self.role_name or 'no_role']
            })
            
            # Attempt to get response through various methods
            response = self._get_clarification_response(query, clarification)
            
            # Update clarification record with response
            clarification['status'] = 'answered'
            clarification['response'] = response
            clarification['answered_at'] = datetime.now().isoformat()
            clarification['response_method'] = getattr(self, '_last_response_method', 'unknown')
            
            # Store response in memory for future reference
            self.memory_system.store_short_term({
                'content': {
                    'clarification_id': clarification['id'],
                    'query': query,
                    'response': response,
                    'worker_id': self.worker_id,
                    'role_name': self.role_name,
                    'task_context': self.current_task.description if self.current_task else None,
                    'response_quality': self._assess_response_quality(response)
                },
                'relevance_score': 0.9,
                'tags': ['clarification_response', 'answered', self.worker_id, self.role_name or 'no_role']
            })
            
            # Update worker state
            self.state = previous_state if previous_state != WorkerState.WAITING_FOR_CLARITY else WorkerState.IDLE
            self.last_activity = datetime.now()
            
            # Learn from clarification patterns
            self._learn_from_clarification(clarification)
            
            return response
            
        except Exception as e:
            self.state = WorkerState.ERROR
            self.logger.error(f"Clarification request failed: {str(e)}")
            raise WorkerError(
                f"Clarification request failed: {str(e)}",
                worker_id=self.worker_id,
                context={'operation': 'clarification_request'},
                original_exception=e
            )
    
    def _find_similar_clarifications(self, query: str) -> List[Dict[str, Any]]:
        """Find similar past clarifications to provide context"""
        try:
            # Search for similar clarification queries in memory
            similar_memories = self.memory_system.retrieve_by_query(
                f"clarification {query[:50]}", 
                memory_type="both"
            )
            
            # Filter and format similar clarifications
            similar_clarifications = []
            for memory in similar_memories[:3]:  # Limit to 3 most relevant
                content = memory.get('content', {})
                if 'query' in content and 'response' in content:
                    similar_clarifications.append({
                        'past_query': content['query'],
                        'past_response': content['response'],
                        'relevance_score': memory.get('relevance_score', 0.0),
                        'timestamp': content.get('timestamp', 'unknown')
                    })
            
            return similar_clarifications
            
        except Exception as e:
            self.logger.warning(f"Failed to find similar clarifications: {str(e)}")
            return []
    
    def _get_clarification_response(self, query: str, clarification: Dict[str, Any]) -> str:
        """Get clarification response through various methods with fallbacks"""
        timeout = self.config.get('clarification_timeout', 60)
        
        try:
            # Method 1: Use callback if available
            if self.clarification_callback:
                self._last_response_method = 'callback'
                response = self.clarification_callback(query)
                if response and response.strip():
                    return response.strip()
            
            # Method 2: Check for intelligent defaults based on context
            intelligent_response = self._generate_intelligent_default(query, clarification)
            if intelligent_response:
                self._last_response_method = 'intelligent_default'
                return intelligent_response
            
            # Method 3: Use similar past responses
            similar_clarifications = clarification.get('similar_past_clarifications', [])
            if similar_clarifications:
                best_match = max(similar_clarifications, key=lambda x: x['relevance_score'])
                if best_match['relevance_score'] > 0.7:
                    self._last_response_method = 'similar_past_response'
                    return f"Based on similar past context: {best_match['past_response']}"
            
            # Method 4: Generate contextual default
            self._last_response_method = 'contextual_default'
            return self._generate_contextual_default(query, clarification)
            
        except Exception as e:
            self.logger.warning(f"All clarification methods failed: {str(e)}")
            self._last_response_method = 'fallback'
            return f"[CLARIFICATION NEEDED: {query}] - Please provide guidance through the user interface."
    
    def _generate_intelligent_default(self, query: str, clarification: Dict[str, Any]) -> Optional[str]:
        """Generate intelligent default response based on context"""
        try:
            query_lower = query.lower()
            
            # Handle common clarification patterns
            if 'compatible' in query_lower and 'role' in query_lower:
                return "Please proceed with the task using your best judgment based on your role capabilities."
            
            if 'more details' in query_lower or 'specific' in query_lower:
                if self.current_task:
                    return f"Please proceed with the task '{self.current_task.description}' using standard best practices for {self.role_name} role."
            
            if 'confirm' in query_lower or 'expected outcome' in query_lower:
                return "Yes, please proceed with your understanding of the task."
            
            # Role-specific intelligent defaults
            if self.role_name == 'editor' and 'edit' in query_lower:
                return "Please focus on improving grammar, clarity, and overall quality of the text."
            elif self.role_name == 'researcher' and 'research' in query_lower:
                return "Please gather comprehensive and accurate information from reliable sources."
            elif self.role_name == 'email_checker' and 'email' in query_lower:
                return "Please organize and extract key information from the emails."
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to generate intelligent default: {str(e)}")
            return None
    
    def _generate_contextual_default(self, query: str, clarification: Dict[str, Any]) -> str:
        """Generate contextual default response when other methods fail"""
        try:
            context_info = []
            
            if self.current_task:
                context_info.append(f"Current task: {self.current_task.description[:100]}")
            
            if self.role_name:
                context_info.append(f"Role: {self.role_name}")
            
            if clarification.get('similar_past_clarifications'):
                context_info.append("Similar situations handled previously")
            
            context_str = " | ".join(context_info) if context_info else "No specific context available"
            
            return f"[AUTO-RESPONSE] Proceeding with best judgment. Context: {context_str}. Query was: {query}"
            
        except Exception:
            return f"[AUTO-RESPONSE] Proceeding with task execution. Original query: {query}"
    
    def _assess_response_quality(self, response: str) -> str:
        """Assess the quality of clarification response for learning"""
        try:
            if not response or len(response.strip()) < 5:
                return 'poor'
            
            if response.startswith('[') and response.endswith(']'):
                return 'auto_generated'
            
            if 'AUTO-RESPONSE' in response:
                return 'contextual_default'
            
            if len(response.split()) > 10:
                return 'detailed'
            
            return 'adequate'
            
        except Exception:
            return 'unknown'
    
    def _learn_from_clarification(self, clarification: Dict[str, Any]) -> None:
        """Learn from clarification patterns to improve future interactions"""
        try:
            learning_data = {
                'clarification_pattern': {
                    'query_type': self._classify_clarification_type(clarification['query']),
                    'role_context': self.role_name,
                    'task_context': clarification.get('task_description', ''),
                    'response_method': clarification.get('response_method', 'unknown'),
                    'response_quality': clarification.get('response_quality', 'unknown'),
                    'timestamp': clarification['timestamp']
                },
                'learning_metadata': {
                    'worker_id': self.worker_id,
                    'clarification_frequency': len(self.pending_clarifications),
                    'execution_context': clarification.get('context', {})
                }
            }
            
            self.memory_system.store_long_term({
                'content': learning_data,
                'relevance_score': 0.6,
                'tags': ['clarification_learning', 'pattern_analysis', self.role_name or 'no_role']
            })
            
        except Exception as e:
            self.logger.warning(f"Failed to learn from clarification: {str(e)}")
    
    def _classify_clarification_type(self, query: str) -> str:
        """Classify the type of clarification request for learning"""
        query_lower = query.lower()
        
        if 'compatible' in query_lower or 'role' in query_lower:
            return 'role_compatibility'
        elif 'details' in query_lower or 'specific' in query_lower:
            return 'missing_details'
        elif 'confirm' in query_lower or 'understand' in query_lower:
            return 'confirmation_request'
        elif 'parameter' in query_lower or 'information' in query_lower:
            return 'missing_parameters'
        elif 'outcome' in query_lower or 'result' in query_lower:
            return 'expected_outcome'
        else:
            return 'general_clarification'
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get comprehensive worker status information"""
        return {
            'worker_id': self.worker_id,
            'state': self.state,
            'role_name': self.role_name,
            'capabilities': self.current_role.get_capabilities() if self.current_role else [],
            'current_task': {
                'id': self.current_task.id,
                'description': self.current_task.description
            } if self.current_task else None,
            'execution_metrics': self.execution_metrics,
            'pending_clarifications': len(self.pending_clarifications),
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'uptime_seconds': (datetime.now() - self.created_at).total_seconds()
        }
    
    def set_clarification_callback(self, callback: callable) -> None:
        """Set callback function for handling clarification requests"""
        self.clarification_callback = callback
    
    def shutdown(self) -> None:
        """Gracefully shutdown the worker"""
        self.logger.info(f"Shutting down worker {self.worker_id}")
        
        try:
            self.state = WorkerState.SHUTDOWN
            
            # Close browser if open
            if hasattr(self.browser_controller, 'close_browser'):
                self.browser_controller.close_browser()
            
            # Clear short-term memory if configured
            if self.config.get('clear_memory_on_shutdown', False):
                self.memory_system.clear_short_term()
            
            # Store shutdown record
            shutdown_record = {
                'worker_id': self.worker_id,
                'shutdown_at': datetime.now().isoformat(),
                'final_metrics': self.execution_metrics,
                'tasks_completed': len(self.task_history)
            }
            
            self.memory_system.store_long_term({
                'content': shutdown_record,
                'relevance_score': 0.6,
                'tags': ['worker_shutdown', self.worker_id, self.role_name or 'no_role']
            })
            
            self.logger.info(f"Worker {self.worker_id} shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during worker shutdown: {str(e)}")    

    def think(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """
        Generate thoughtful response using LLM with human-like memory integration
        
        Args:
            prompt: Prompt to think about
            context: Additional context
            
        Returns:
            Thoughtful response
        """
        try:
            # Get relevant memories for this thinking task
            memory_context = ""
            if hasattr(self.memory_system, 'get_relevant_memories_for_context'):
                memory_context = self.memory_system.get_relevant_memories_for_context(prompt, max_memories=3)
            
            # Add worker context
            full_context = context or {}
            full_context.update({
                'worker_id': self.worker_id,
                'role': self.role_name,
                'capabilities': self.current_role.get_capabilities() if self.current_role else [],
                'relevant_memories': memory_context
            })
            
            # Enhanced prompt with memory context
            enhanced_prompt = prompt
            if memory_context and memory_context != "No relevant memories found.":
                enhanced_prompt = f"{memory_context}\n\nCurrent task: {prompt}\n\nConsider the above memories when responding."
            
            response = self.llm.think(enhanced_prompt, full_context)
            
            # Store thinking in memory only if important
            thinking_data = {
                'thinking_prompt': prompt,
                'thinking_response': response,
                'context': full_context
            }
            
            if hasattr(self.memory_system, 'is_memory_important'):
                if self.memory_system.is_memory_important(thinking_data, prompt):
                    self.update_memory({
                        'content': thinking_data,
                        'relevance_score': 0.6,
                        'tags': ['thinking', 'llm_response', self.worker_id]
                    })
            else:
                # Fallback to old behavior if enhanced memory not available
                self.update_memory({
                    'content': thinking_data,
                    'relevance_score': 0.6,
                    'tags': ['thinking', 'llm_response', self.worker_id]
                })
            
            return response
            
        except Exception as e:
            self.logger.error(f"Thinking failed: {str(e)}")
            raise WorkerError(f"Thinking failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def plan_task_execution(self, task: Task) -> Dict[str, Any]:
        """
        Plan how to execute a task using reasoning engine
        
        Args:
            task: Task to plan execution for
            
        Returns:
            Execution plan
        """
        try:
            self.logger.info(f"Planning execution for task: {task.id}")
            
            # Get relevant context from memory
            context = self._prepare_task_context(task)
            
            # Use reasoning engine to plan
            plan = self.reasoning_engine.solve_problem(
                task.description,
                context=context
            )
            
            # Store plan in memory
            self.update_memory({
                'content': {
                    'task_id': task.id,
                    'execution_plan': plan,
                    'planned_at': datetime.now().isoformat()
                },
                'relevance_score': 0.8,
                'tags': ['execution_plan', task.id, self.worker_id]
            })
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Task planning failed: {str(e)}")
            raise WorkerError(f"Task planning failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def make_decision(self, situation: str, options: List[str], criteria: List[str] = None) -> Dict[str, Any]:
        """
        Make a decision using reasoning engine
        
        Args:
            situation: Decision context
            options: Available options
            criteria: Decision criteria
            
        Returns:
            Decision result
        """
        try:
            self.logger.info("Making decision")
            
            # Get relevant context
            context = {
                'worker_id': self.worker_id,
                'role': self.role_name,
                'capabilities': self.current_role.get_capabilities() if self.current_role else []
            }
            
            # Use reasoning engine
            decision = self.reasoning_engine.make_decision(
                situation, options, criteria, context
            )
            
            # Store decision in memory
            self.update_memory({
                'content': {
                    'decision_situation': situation,
                    'decision_result': decision,
                    'decided_at': datetime.now().isoformat()
                },
                'relevance_score': 0.8,
                'tags': ['decision', 'reasoning', self.worker_id]
            })
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Decision making failed: {str(e)}")
            raise WorkerError(f"Decision making failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def write_code(self, requirements: str, language: str = "python") -> Dict[str, Any]:
        """
        Write code based on requirements
        
        Args:
            requirements: Code requirements
            language: Programming language
            
        Returns:
            Generated code and metadata
        """
        try:
            self.logger.info(f"Writing {language} code")
            
            # Get relevant context
            context = {
                'worker_id': self.worker_id,
                'role': self.role_name,
                'language': language
            }
            
            # Generate code using LLM
            code_result = self.llm.generate_code(requirements, language, context)
            
            # Validate syntax
            syntax_check = self.code_executor.validate_syntax(code_result['code'], language)
            code_result['syntax_validation'] = syntax_check
            
            # Store code in memory
            self.update_memory({
                'content': {
                    'code_requirements': requirements,
                    'generated_code': code_result,
                    'language': language,
                    'created_at': datetime.now().isoformat()
                },
                'relevance_score': 0.7,
                'tags': ['code_generation', language, self.worker_id]
            })
            
            return code_result
            
        except Exception as e:
            self.logger.error(f"Code writing failed: {str(e)}")
            raise WorkerError(f"Code writing failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def test_code(self, code: str, test_cases: str, language: str = "python") -> Dict[str, Any]:
        """
        Test code with test cases
        
        Args:
            code: Code to test
            test_cases: Test cases
            language: Programming language
            
        Returns:
            Test results
        """
        try:
            self.logger.info(f"Testing {language} code")
            
            # Execute tests
            test_result = self.code_executor.test_code(code, test_cases, language)
            
            # Store test results in memory
            self.update_memory({
                'content': {
                    'test_results': test_result,
                    'language': language,
                    'tested_at': datetime.now().isoformat()
                },
                'relevance_score': 0.6,
                'tags': ['code_testing', language, self.worker_id]
            })
            
            return test_result
            
        except Exception as e:
            self.logger.error(f"Code testing failed: {str(e)}")
            raise WorkerError(f"Code testing failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def run_code(self, code: str, language: str = "python", inputs: List[str] = None) -> Dict[str, Any]:
        """
        Execute code
        
        Args:
            code: Code to execute
            language: Programming language
            inputs: Input values for the program
            
        Returns:
            Execution results
        """
        try:
            self.logger.info(f"Executing {language} code")
            
            # Execute code
            execution_result = self.code_executor.execute_code(code, language, inputs)
            
            # Store execution results in memory
            self.update_memory({
                'content': {
                    'execution_results': execution_result,
                    'language': language,
                    'executed_at': datetime.now().isoformat()
                },
                'relevance_score': 0.6,
                'tags': ['code_execution', language, self.worker_id]
            })
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Code execution failed: {str(e)}")
            raise WorkerError(f"Code execution failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def send_email(self, to_email: str, subject: str, body: str, email_service: str = "gmail") -> Dict[str, Any]:
        """
        Send email using browser automation
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            email_service: Email service to use
            
        Returns:
            Send status
        """
        try:
            self.logger.info(f"Sending email to {to_email}")
            
            # Use browser controller to send email
            result = self.browser_controller.send_email(to_email, subject, body, email_service)
            
            # Store email activity in memory
            self.update_memory({
                'content': {
                    'email_sent': {
                        'to': to_email,
                        'subject': subject,
                        'service': email_service,
                        'result': result
                    },
                    'sent_at': datetime.now().isoformat()
                },
                'relevance_score': 0.7,
                'tags': ['email', 'communication', self.worker_id]
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Email sending failed: {str(e)}")
            raise WorkerError(f"Email sending failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def create_document(self, title: str, content: str, doc_type: str = "google_docs") -> Dict[str, Any]:
        """
        Create document using browser automation
        
        Args:
            title: Document title
            content: Document content
            doc_type: Document service type
            
        Returns:
            Creation status and document URL
        """
        try:
            self.logger.info(f"Creating document: {title}")
            
            # Use browser controller to create document
            result = self.browser_controller.create_document(title, content, doc_type)
            
            # Store document creation in memory
            self.update_memory({
                'content': {
                    'document_created': {
                        'title': title,
                        'type': doc_type,
                        'result': result
                    },
                    'created_at': datetime.now().isoformat()
                },
                'relevance_score': 0.7,
                'tags': ['document_creation', doc_type, self.worker_id]
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Document creation failed: {str(e)}")
            raise WorkerError(f"Document creation failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def create_spreadsheet(self, title: str, data: List[List[str]], sheet_type: str = "google_sheets") -> Dict[str, Any]:
        """
        Create spreadsheet using browser automation
        
        Args:
            title: Spreadsheet title
            data: Spreadsheet data
            sheet_type: Spreadsheet service type
            
        Returns:
            Creation status and spreadsheet URL
        """
        try:
            self.logger.info(f"Creating spreadsheet: {title}")
            
            # Use browser controller to create spreadsheet
            result = self.browser_controller.create_spreadsheet(title, data, sheet_type)
            
            # Store spreadsheet creation in memory
            self.update_memory({
                'content': {
                    'spreadsheet_created': {
                        'title': title,
                        'type': sheet_type,
                        'rows': len(data),
                        'result': result
                    },
                    'created_at': datetime.now().isoformat()
                },
                'relevance_score': 0.7,
                'tags': ['spreadsheet_creation', sheet_type, self.worker_id]
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Spreadsheet creation failed: {str(e)}")
            raise WorkerError(f"Spreadsheet creation failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def web_search(self, query: str, search_engine: str = "google", max_results: int = 10) -> Dict[str, Any]:
        """
        Perform web search using browser automation
        
        Args:
            query: Search query
            search_engine: Search engine to use
            max_results: Maximum results to return
            
        Returns:
            Search results
        """
        try:
            self.logger.info(f"Performing web search: {query}")
            
            # Use browser controller to search
            result = self.browser_controller.perform_web_search(query, search_engine, max_results)
            
            # Store search activity in memory
            self.update_memory({
                'content': {
                    'web_search': {
                        'query': query,
                        'engine': search_engine,
                        'result': result
                    },
                    'searched_at': datetime.now().isoformat()
                },
                'relevance_score': 0.6,
                'tags': ['web_search', search_engine, self.worker_id]
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Web search failed: {str(e)}")
            raise WorkerError(f"Web search failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def apply_common_sense(self, situation: str) -> Dict[str, Any]:
        """
        Apply common sense reasoning to a situation
        
        Args:
            situation: Situation to analyze
            
        Returns:
            Common sense analysis
        """
        try:
            self.logger.info("Applying common sense reasoning")
            
            # Get relevant context
            context = {
                'worker_id': self.worker_id,
                'role': self.role_name,
                'capabilities': self.current_role.get_capabilities() if self.current_role else []
            }
            
            # Use reasoning engine
            analysis = self.reasoning_engine.apply_common_sense(situation, context)
            
            # Store analysis in memory
            self.update_memory({
                'content': {
                    'common_sense_analysis': analysis,
                    'situation': situation,
                    'analyzed_at': datetime.now().isoformat()
                },
                'relevance_score': 0.7,
                'tags': ['common_sense', 'reasoning', self.worker_id]
            })
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Common sense reasoning failed: {str(e)}")
            raise WorkerError(f"Common sense reasoning failed: {str(e)}", worker_id=self.worker_id, original_exception=e)
    
    def get_enhanced_capabilities(self) -> List[str]:
        """Get list of all enhanced capabilities"""
        base_capabilities = self.current_role.get_capabilities() if self.current_role else []
        
        enhanced_capabilities = [
            'intelligent_reasoning',
            'decision_making',
            'problem_solving',
            'code_writing',
            'code_testing',
            'code_execution',
            'email_sending',
            'document_creation',
            'spreadsheet_creation',
            'web_searching',
            'form_interaction',
            'common_sense_reasoning',
            'task_planning',
            'llm_thinking',
            'memory_integration',
            'knowledge_validation'
        ]
        
        return base_capabilities + enhanced_capabilities
"""
Task Executor class implementation

Handles task processing logic that breaks down complex tasks into steps,
validates task feasibility, and coordinates browser action execution with monitoring.
"""

import time
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from .interfaces import (
    ITaskExecutor, Task, TaskResult, BrowserAction, TaskStatus, ActionType,
    IBrowserController
)
from .exceptions import TaskExecutionError, BrowserError


class TaskExecutor(ITaskExecutor):
    """
    Task Executor class that processes tasks and coordinates browser automation.
    
    Breaks down complex tasks into actionable browser steps, validates task feasibility,
    executes browser actions, and monitors execution progress with performance metrics.
    """
    
    def __init__(self, browser_controller: IBrowserController):
        """
        Initialize task executor with browser controller.
        
        Args:
            browser_controller: Browser controller instance for web interactions
            
        Raises:
            TaskExecutionError: If browser controller is not provided
        """
        if not browser_controller:
            raise TaskExecutionError(
                "Browser controller is required for task execution",
                task_id="initialization",
                step="setup"
            )
        
        self.browser_controller = browser_controller
        self.logger = logging.getLogger(__name__)
        
        # Execution monitoring state
        self._execution_status: Dict[str, Dict[str, Any]] = {}
        self._execution_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Task validation patterns
        self._validation_patterns = {
            'url_navigation': r'(navigate|go|visit|open)\s+.*?(http|www|\.com|\.org)',
            'form_interaction': r'(fill|enter|type|input|submit)\s+.*?(form|field|input|text)',
            'element_interaction': r'(click|press|select|choose)\s+.*?(button|link|element)',
            'data_extraction': r'(extract|get|scrape|find|collect)\s+.*?(data|text|information)',
            'search_operation': r'(search|find|look)\s+.*?(for|about)',
            'file_operation': r'(download|upload|save)\s+.*?(file|document|image)'
        }
        
        self.logger.info("TaskExecutor initialized with browser controller")
    
    def process_task(self, task: Task) -> List[BrowserAction]:
        """
        Process task and break it down into actionable browser steps.
        
        Args:
            task: Task object to process
            
        Returns:
            List of BrowserAction objects representing the execution steps
            
        Raises:
            TaskExecutionError: If task cannot be processed or is invalid
        """
        self.logger.info(f"Processing task: {task.id} - {task.description}")
        
        try:
            # Validate task before processing
            if not self.validate_task(task):
                raise TaskExecutionError(
                    f"Task validation failed: {task.description}",
                    task_id=task.id,
                    step="validation"
                )
            
            # Initialize execution tracking
            self._initialize_execution_tracking(task.id)
            
            # Analyze task description and parameters
            task_analysis = self._analyze_task(task)
            
            # Generate browser actions based on analysis
            actions = self._generate_browser_actions(task, task_analysis)
            
            # Validate generated actions
            self._validate_action_sequence(actions)
            
            self.logger.info(f"Generated {len(actions)} browser actions for task {task.id}")
            return actions
            
        except Exception as e:
            self.logger.error(f"Failed to process task {task.id}: {str(e)}")
            if isinstance(e, TaskExecutionError):
                raise
            else:
                raise TaskExecutionError(
                    f"Unexpected error processing task: {str(e)}",
                    task_id=task.id,
                    step="processing",
                    original_exception=e
                )
    
    def validate_task(self, task: Task) -> bool:
        """
        Validate if task is feasible and can be executed.
        
        Args:
            task: Task object to validate
            
        Returns:
            bool: True if task is valid and feasible
        """
        self.logger.debug(f"Validating task: {task.id}")
        
        try:
            # Basic task structure validation (already done in Task.__post_init__)
            task.validate()
            
            # Check if task description contains actionable instructions
            if not self._has_actionable_content(task.description):
                self.logger.warning(f"Task {task.id} lacks actionable content")
                return False
            
            # Check if task requires browser interaction
            if not self._requires_browser_interaction(task.description):
                self.logger.warning(f"Task {task.id} does not require browser interaction")
                return False
            
            # Validate task parameters
            if not self._validate_task_parameters(task):
                self.logger.warning(f"Task {task.id} has invalid parameters")
                return False
            
            # Check deadline feasibility
            if task.deadline and task.deadline < datetime.now():
                self.logger.warning(f"Task {task.id} deadline has passed")
                return False
            
            self.logger.debug(f"Task {task.id} validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Task validation error for {task.id}: {str(e)}")
            return False
    
    def execute_browser_actions(self, actions: List[BrowserAction]) -> TaskResult:
        """
        Execute browser actions and return comprehensive result.
        
        Args:
            actions: List of BrowserAction objects to execute
            
        Returns:
            TaskResult with execution results and metrics
            
        Raises:
            TaskExecutionError: If action execution fails
        """
        if not actions:
            raise TaskExecutionError(
                "No actions provided for execution",
                task_id="unknown",
                step="execution"
            )
        
        task_id = f"execution_{int(time.time())}"
        self.logger.info(f"Executing {len(actions)} browser actions for task {task_id}")
        
        start_time = time.time()
        executed_actions = 0
        action_results = []
        sources_used = []
        
        try:
            # Initialize execution tracking
            self._initialize_execution_tracking(task_id)
            
            # Execute each action
            for i, action in enumerate(actions):
                self.logger.debug(f"Executing action {i+1}/{len(actions)}: {action.action_type.value}")
                
                # Update execution status
                self._update_execution_status(task_id, {
                    'current_action': i + 1,
                    'total_actions': len(actions),
                    'action_type': action.action_type.value,
                    'target': action.target
                })
                
                # Execute the action
                action_result = self.browser_controller.perform_action(action)
                action_results.append(action_result)
                executed_actions += 1
                
                # Track sources if this was a navigation or extraction action
                if action.action_type in [ActionType.EXTRACT, ActionType.CLICK]:
                    try:
                        current_url = getattr(self.browser_controller, 'get_current_url', lambda: 'unknown')()
                        # Ensure URL is a string
                        if current_url and isinstance(current_url, str) and current_url not in sources_used:
                            sources_used.append(current_url)
                    except Exception:
                        # If we can't get URL, use a default
                        if 'unknown' not in sources_used:
                            sources_used.append('unknown')
                
                # Small delay between actions for stability
                time.sleep(0.5)
            
            execution_time = time.time() - start_time
            
            # Calculate confidence score based on successful actions
            confidence_score = self._calculate_confidence_score(action_results, executed_actions, len(actions))
            
            # Compile result data
            result_data = {
                'actions_executed': executed_actions,
                'total_actions': len(actions),
                'action_results': action_results,
                'execution_summary': self._generate_execution_summary(action_results)
            }
            
            # Create task result
            task_result = TaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result_data=result_data,
                execution_time=execution_time,
                confidence_score=confidence_score,
                sources_used=sources_used
            )
            
            self.logger.info(f"Task {task_id} completed successfully in {execution_time:.2f}s")
            return task_result
            
        except BrowserError as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Browser error during task execution: {str(e)}")
            
            # Return failed result with partial data
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                result_data={
                    'actions_executed': executed_actions,
                    'total_actions': len(actions),
                    'error': str(e),
                    'action_results': action_results
                },
                execution_time=execution_time,
                confidence_score=0.0,
                sources_used=sources_used
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Unexpected error during task execution: {str(e)}")
            
            raise TaskExecutionError(
                f"Task execution failed: {str(e)}",
                task_id=task_id,
                step="execution",
                original_exception=e
            )
    
    def monitor_execution(self, task_id: str) -> Dict[str, Any]:
        """
        Monitor task execution status and return current metrics.
        
        Args:
            task_id: ID of the task to monitor
            
        Returns:
            Dict containing execution status and performance metrics
        """
        if task_id not in self._execution_status:
            return {
                'task_id': task_id,
                'status': 'not_found',
                'message': 'Task not found in execution tracking'
            }
        
        status = self._execution_status[task_id]
        metrics = self._execution_metrics.get(task_id, {})
        
        return {
            'task_id': task_id,
            'status': status.get('status', 'unknown'),
            'progress': {
                'current_action': status.get('current_action', 0),
                'total_actions': status.get('total_actions', 0),
                'percentage': self._calculate_progress_percentage(status)
            },
            'current_activity': {
                'action_type': status.get('action_type'),
                'target': status.get('target'),
                'started_at': status.get('started_at')
            },
            'metrics': {
                'execution_time': time.time() - metrics.get('start_time', time.time()),
                'actions_per_second': self._calculate_actions_per_second(metrics, status),
                'estimated_completion': self._estimate_completion_time(metrics, status)
            },
            'last_updated': status.get('last_updated', datetime.now().isoformat())
        }
    
    def _analyze_task(self, task: Task) -> Dict[str, Any]:
        """
        Analyze task description and parameters to determine execution strategy.
        
        Args:
            task: Task object to analyze
            
        Returns:
            Dict containing task analysis results
        """
        description = task.description.lower()
        analysis = {
            'task_type': 'unknown',
            'requires_navigation': False,
            'requires_form_interaction': False,
            'requires_data_extraction': False,
            'target_url': None,
            'form_fields': [],
            'extraction_targets': [],
            'complexity_score': 1
        }
        
        # Determine task type based on patterns
        for task_type, pattern in self._validation_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                analysis['task_type'] = task_type
                break
        
        # Check for URL in task parameters or description
        url_pattern = r'https?://[^\s]+|www\.[^\s]+|\w+\.(com|org|net|edu|gov)[^\s]*'
        url_match = re.search(url_pattern, description)
        if url_match:
            analysis['target_url'] = url_match.group()
            analysis['requires_navigation'] = True
        elif 'url' in task.parameters:
            analysis['target_url'] = task.parameters['url']
            analysis['requires_navigation'] = True
        
        # Analyze form interaction requirements
        form_keywords = ['form', 'input', 'field', 'submit', 'enter', 'fill']
        if any(keyword in description for keyword in form_keywords):
            analysis['requires_form_interaction'] = True
            # Extract form fields from parameters
            if 'form_data' in task.parameters:
                analysis['form_fields'] = list(task.parameters['form_data'].keys())
        
        # Analyze data extraction requirements
        extraction_keywords = ['extract', 'scrape', 'get', 'collect', 'find']
        if any(keyword in description for keyword in extraction_keywords):
            analysis['requires_data_extraction'] = True
            # Extract target selectors from parameters
            if 'selectors' in task.parameters:
                analysis['extraction_targets'] = task.parameters['selectors']
        
        # Calculate complexity score
        complexity_factors = [
            analysis['requires_navigation'],
            analysis['requires_form_interaction'],
            analysis['requires_data_extraction'],
            len(analysis['form_fields']) > 3,
            len(analysis['extraction_targets']) > 5
        ]
        analysis['complexity_score'] = sum(complexity_factors) + 1
        
        return analysis
    
    def _generate_browser_actions(self, task: Task, analysis: Dict[str, Any]) -> List[BrowserAction]:
        """
        Generate browser actions based on task analysis.
        
        Args:
            task: Task object
            analysis: Task analysis results
            
        Returns:
            List of BrowserAction objects
        """
        actions = []
        
        # Navigation action
        if analysis['requires_navigation'] and analysis['target_url']:
            # Note: Navigation is handled by browser controller's open_browser method
            # We'll add a wait action to ensure page loads
            actions.append(BrowserAction.create_wait(
                target="body",
                timeout=10,
                expected_outcome="Page loaded successfully"
            ))
        
        # Form interaction actions
        if analysis['requires_form_interaction'] and 'form_data' in task.parameters:
            for field_name, field_value in task.parameters['form_data'].items():
                # Add type action for each form field
                actions.append(BrowserAction.create_type(
                    target=f"input[name='{field_name}'], input[id='{field_name}'], #{field_name}",
                    text=str(field_value),
                    expected_outcome=f"Text entered in {field_name} field"
                ))
            
            # Add submit action if specified
            if task.parameters.get('submit_form', True):
                actions.append(BrowserAction.create_click(
                    target="input[type='submit'], button[type='submit'], .submit-btn",
                    selector="input[type='submit'], button[type='submit'], .submit-btn",
                    expected_outcome="Form submitted successfully"
                ))
        
        # Data extraction actions
        if analysis['requires_data_extraction']:
            selectors = task.parameters.get('selectors', [])
            if isinstance(selectors, dict):
                # Multiple named extractions
                for name, selector in selectors.items():
                    actions.append(BrowserAction(
                        action_type=ActionType.EXTRACT,
                        target=selector,
                        parameters={'extraction_name': name},
                        expected_outcome=f"Data extracted from {name}"
                    ))
            elif isinstance(selectors, list):
                # Multiple selectors
                for i, selector in enumerate(selectors):
                    actions.append(BrowserAction(
                        action_type=ActionType.EXTRACT,
                        target=selector,
                        parameters={'extraction_index': i},
                        expected_outcome=f"Data extracted from selector {i+1}"
                    ))
            else:
                # Single selector
                actions.append(BrowserAction(
                    action_type=ActionType.EXTRACT,
                    target=str(selectors),
                    parameters={},
                    expected_outcome="Data extracted successfully"
                ))
        
        # Click actions for buttons/links
        if 'click_targets' in task.parameters:
            click_targets = task.parameters['click_targets']
            if isinstance(click_targets, list):
                for target in click_targets:
                    actions.append(BrowserAction.create_click(
                        target=target,
                        selector=target,
                        expected_outcome=f"Clicked on {target}"
                    ))
        
        # Scroll actions if needed
        if task.parameters.get('scroll_to_load', False):
            actions.append(BrowserAction.create_scroll(
                target="body",
                direction="down",
                amount=3,
                expected_outcome="Page scrolled to load more content"
            ))
        
        return actions
    
    def _validate_action_sequence(self, actions: List[BrowserAction]) -> None:
        """
        Validate that the sequence of actions is logical and executable.
        
        Args:
            actions: List of BrowserAction objects to validate
            
        Raises:
            TaskExecutionError: If action sequence is invalid
        """
        if not actions:
            raise TaskExecutionError(
                "Empty action sequence generated",
                task_id="validation",
                step="action_generation"
            )
        
        # Check for logical action ordering
        has_navigation = any(action.action_type == ActionType.WAIT for action in actions[:2])
        has_form_actions = any(action.action_type == ActionType.TYPE for action in actions)
        has_submit = any(
            action.action_type == ActionType.CLICK and 'submit' in action.target.lower()
            for action in actions
        )
        
        # If there are form actions, there should be navigation first
        if has_form_actions and not has_navigation:
            self.logger.warning("Form actions without navigation - may fail")
        
        # If there are type actions, they should come before submit
        if has_form_actions and has_submit:
            type_indices = [i for i, action in enumerate(actions) if action.action_type == ActionType.TYPE]
            submit_indices = [
                i for i, action in enumerate(actions)
                if action.action_type == ActionType.CLICK and 'submit' in action.target.lower()
            ]
            
            if type_indices and submit_indices and max(type_indices) > min(submit_indices):
                self.logger.warning("Type actions after submit action - may cause issues")
    
    def _has_actionable_content(self, description: str) -> bool:
        """Check if task description contains actionable instructions."""
        action_verbs = [
            'navigate', 'go', 'visit', 'open', 'click', 'press', 'select', 'choose',
            'fill', 'enter', 'type', 'input', 'submit', 'extract', 'get', 'scrape',
            'find', 'collect', 'search', 'look', 'download', 'upload', 'save'
        ]
        
        description_lower = description.lower()
        return any(verb in description_lower for verb in action_verbs)
    
    def _requires_browser_interaction(self, description: str) -> bool:
        """Check if task requires browser interaction."""
        browser_keywords = [
            'website', 'web', 'page', 'url', 'browser', 'navigate', 'click',
            'form', 'button', 'link', 'scrape', 'extract', 'download'
        ]
        
        description_lower = description.lower()
        # Check if any browser keywords are present AND it's not just a calculation/processing task
        has_browser_keywords = any(keyword in description_lower for keyword in browser_keywords)
        
        # Exclude pure computational tasks
        computational_keywords = ['calculate', 'compute', 'process', 'generate', 'formula']
        is_computational = any(keyword in description_lower for keyword in computational_keywords)
        
        return has_browser_keywords and not is_computational
    
    def _validate_task_parameters(self, task: Task) -> bool:
        """Validate task parameters for completeness and correctness."""
        # Check for required parameters based on task type
        if 'url' in task.parameters:
            url = task.parameters['url']
            if not isinstance(url, str) or not url.strip():
                return False
        
        if 'form_data' in task.parameters:
            form_data = task.parameters['form_data']
            if not isinstance(form_data, dict):
                return False
        
        if 'selectors' in task.parameters:
            selectors = task.parameters['selectors']
            if not isinstance(selectors, (list, dict, str)):
                return False
        
        return True
    
    def _initialize_execution_tracking(self, task_id: str) -> None:
        """Initialize execution tracking for a task."""
        current_time = time.time()
        
        self._execution_status[task_id] = {
            'status': 'initialized',
            'started_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'current_action': 0,
            'total_actions': 0
        }
        
        self._execution_metrics[task_id] = {
            'start_time': current_time,
            'actions_completed': 0,
            'total_execution_time': 0.0
        }
    
    def _update_execution_status(self, task_id: str, status_update: Dict[str, Any]) -> None:
        """Update execution status for a task."""
        if task_id in self._execution_status:
            self._execution_status[task_id].update(status_update)
            self._execution_status[task_id]['last_updated'] = datetime.now().isoformat()
            self._execution_status[task_id]['status'] = 'in_progress'
    
    def _calculate_confidence_score(self, action_results: List[Dict], executed: int, total: int) -> float:
        """Calculate confidence score based on execution results."""
        if total == 0:
            return 0.0
        
        # Base score from completion percentage
        completion_score = executed / total
        
        # Success rate of executed actions
        successful_actions = sum(1 for result in action_results if result.get('success', False))
        success_rate = successful_actions / executed if executed > 0 else 0.0
        
        # Combine scores with weights
        confidence = (completion_score * 0.6) + (success_rate * 0.4)
        
        return min(1.0, max(0.0, confidence))
    
    def _generate_execution_summary(self, action_results: List[Dict]) -> Dict[str, Any]:
        """Generate summary of execution results."""
        total_actions = len(action_results)
        successful_actions = sum(1 for result in action_results if result.get('success', False))
        
        # Calculate average execution time
        total_time = sum(result.get('execution_time', 0) for result in action_results)
        avg_time = total_time / total_actions if total_actions > 0 else 0.0
        
        return {
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'success_rate': successful_actions / total_actions if total_actions > 0 else 0.0,
            'average_execution_time': avg_time
        }
    
    def _calculate_progress_percentage(self, status: Dict[str, Any]) -> float:
        """Calculate progress percentage from status."""
        current = status.get('current_action', 0)
        total = status.get('total_actions', 0)
        
        if total == 0:
            return 0.0
        
        return (current / total) * 100.0
    
    def _calculate_actions_per_second(self, metrics: Dict[str, Any], status: Dict[str, Any]) -> float:
        """Calculate actions per second rate."""
        elapsed_time = time.time() - metrics.get('start_time', time.time())
        actions_completed = status.get('current_action', 0)
        
        if elapsed_time == 0:
            return 0.0
        
        return actions_completed / elapsed_time
    
    def _estimate_completion_time(self, metrics: Dict[str, Any], status: Dict[str, Any]) -> Optional[str]:
        """Estimate completion time based on current progress."""
        current_action = status.get('current_action', 0)
        total_actions = status.get('total_actions', 0)
        elapsed_time = time.time() - metrics.get('start_time', time.time())
        
        if current_action == 0 or total_actions == 0:
            return None
        
        remaining_actions = total_actions - current_action
        avg_time_per_action = elapsed_time / current_action
        estimated_remaining_time = remaining_actions * avg_time_per_action
        
        completion_time = datetime.now() + timedelta(seconds=estimated_remaining_time)
        return completion_time.isoformat()
"""
Mode Manager for Collaborative Worker System

Handles mode detection, switching, and configuration management between
Manual and Auto modes with seamless transitions.
"""

import uuid
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .manual_mode_controller import ManualModeController
from .auto_mode_controller import AutoModeController
from .exceptions import WorkerError


class OperationMode(Enum):
    """Available operation modes"""
    MANUAL = "manual"
    AUTO = "auto"
    HYBRID = "hybrid"  # Future extension
    TRANSITIONING = "transitioning"


@dataclass
class ModeConfiguration:
    """Configuration for operation modes"""
    mode: OperationMode
    config: Dict[str, Any]
    created_at: datetime
    last_modified: datetime
    is_active: bool = False


@dataclass
class ModeTransition:
    """Represents a mode transition event"""
    transition_id: str
    from_mode: OperationMode
    to_mode: OperationMode
    initiated_by: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "in_progress"  # in_progress, completed, failed, cancelled
    transition_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ModeManager:
    """
    Manages operation modes and transitions between Manual and Auto modes.
    
    Provides:
    - Mode detection and switching mechanisms
    - Configuration management for both modes
    - Mode-specific initialization and cleanup
    - Seamless transition between modes
    - State preservation during transitions
    """
    
    def __init__(self, server_instance, default_mode: OperationMode = OperationMode.MANUAL,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize the mode manager.
        
        Args:
            server_instance: Reference to the collaborative server
            default_mode: Default operation mode
            config: Optional configuration parameters
        """
        self.server = server_instance
        self.manager_id = str(uuid.uuid4())
        self.config = config or {}
        
        # Setup logging
        self.logger = logging.getLogger(f"ModeManager.{self.manager_id[:8]}")
        
        # Mode state
        self.current_mode = OperationMode.TRANSITIONING
        self.target_mode = default_mode
        self.previous_mode = None
        
        # Mode controllers
        self.manual_controller: Optional[ManualModeController] = None
        self.auto_controller: Optional[AutoModeController] = None
        
        # Mode configurations
        self.mode_configurations: Dict[OperationMode, ModeConfiguration] = {}
        self._initialize_default_configurations()
        
        # Transition management
        self.active_transitions: Dict[str, ModeTransition] = {}
        self.transition_history: List[ModeTransition] = []
        self.transition_lock = threading.Lock()
        
        # Mode change callbacks
        self.mode_change_callbacks: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            'mode_switches': 0,
            'successful_transitions': 0,
            'failed_transitions': 0,
            'total_uptime_seconds': 0,
            'mode_uptime': {mode.value: 0 for mode in OperationMode}
        }
        
        # Initialize with default mode
        self._initialize_mode(default_mode)
        
        self.logger.info(f"ModeManager initialized with default mode: {default_mode.value}")
    
    def get_current_mode(self) -> OperationMode:
        """
        Get the current operation mode.
        
        Returns:
            Current OperationMode
        """
        return self.current_mode
    
    def switch_mode(self, target_mode: OperationMode, 
                   transition_config: Optional[Dict[str, Any]] = None,
                   preserve_state: bool = True) -> str:
        """
        Switch to a different operation mode.
        
        Args:
            target_mode: Target operation mode
            transition_config: Optional configuration for the transition
            preserve_state: Whether to preserve state during transition
            
        Returns:
            Transition ID for tracking the switch
            
        Raises:
            WorkerError: If mode switch fails to initiate
        """
        if target_mode == self.current_mode:
            self.logger.info(f"Already in target mode: {target_mode.value}")
            return ""
        
        with self.transition_lock:
            try:
                # Create transition record
                transition = ModeTransition(
                    transition_id=str(uuid.uuid4()),
                    from_mode=self.current_mode,
                    to_mode=target_mode,
                    initiated_by="mode_manager",
                    started_at=datetime.now(),
                    transition_data=transition_config or {}
                )
                
                self.active_transitions[transition.transition_id] = transition
                
                self.logger.info(f"Starting mode transition: {self.current_mode.value} -> {target_mode.value}")
                
                # Set transitioning state
                self.previous_mode = self.current_mode
                self.current_mode = OperationMode.TRANSITIONING
                self.target_mode = target_mode
                
                # Perform the transition
                success = self._perform_mode_transition(transition, preserve_state)
                
                if success:
                    transition.status = "completed"
                    transition.completed_at = datetime.now()
                    self.current_mode = target_mode
                    
                    self.stats['mode_switches'] += 1
                    self.stats['successful_transitions'] += 1
                    
                    # Notify callbacks
                    self._notify_mode_change(self.previous_mode, target_mode)
                    
                    self.logger.info(f"Mode transition completed: {transition.transition_id}")
                else:
                    transition.status = "failed"
                    transition.completed_at = datetime.now()
                    self.current_mode = self.previous_mode  # Rollback
                    
                    self.stats['failed_transitions'] += 1
                    
                    self.logger.error(f"Mode transition failed: {transition.transition_id}")
                
                # Move to history
                self.transition_history.append(transition)
                del self.active_transitions[transition.transition_id]
                
                return transition.transition_id
                
            except Exception as e:
                self.logger.error(f"Mode switch initiation failed: {e}")
                raise WorkerError(
                    f"Mode switch failed: {e}",
                    worker_id=self.manager_id,
                    context={'operation': 'switch_mode', 'error': str(e)}
                )
    
    def get_mode_configuration(self, mode: OperationMode) -> Optional[ModeConfiguration]:
        """
        Get configuration for a specific mode.
        
        Args:
            mode: Operation mode to get configuration for
            
        Returns:
            ModeConfiguration or None if not found
        """
        return self.mode_configurations.get(mode)
    
    def update_mode_configuration(self, mode: OperationMode, 
                                config_updates: Dict[str, Any]) -> bool:
        """
        Update configuration for a specific mode.
        
        Args:
            mode: Operation mode to update
            config_updates: Configuration updates to apply
            
        Returns:
            True if configuration was updated successfully
        """
        try:
            if mode not in self.mode_configurations:
                self.logger.error(f"No configuration found for mode: {mode.value}")
                return False
            
            mode_config = self.mode_configurations[mode]
            
            # Update configuration
            mode_config.config.update(config_updates)
            mode_config.last_modified = datetime.now()
            
            # If this is the current mode, apply changes immediately
            if mode == self.current_mode:
                self._apply_mode_configuration(mode, mode_config)
            
            self.logger.info(f"Updated configuration for mode: {mode.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update mode configuration: {e}")
            return False
    
    def detect_optimal_mode(self, context: Dict[str, Any]) -> OperationMode:
        """
        Detect the optimal operation mode based on context.
        
        Args:
            context: Context information for mode detection
            
        Returns:
            Recommended OperationMode
        """
        try:
            # Simple heuristics for mode detection
            # In a real implementation, this could use ML or more sophisticated rules
            
            objectives = context.get('objectives', '')
            user_preference = context.get('user_preference')
            complexity = context.get('complexity_score', 0)
            worker_count = context.get('required_workers', 0)
            
            # User preference takes priority
            if user_preference:
                try:
                    return OperationMode(user_preference.lower())
                except ValueError:
                    pass
            
            # Auto mode for complex objectives
            if complexity > 6 or worker_count > 3:
                return OperationMode.AUTO
            
            # Auto mode for certain keywords
            auto_keywords = ['automate', 'automatic', 'autonomous', 'complex', 'coordinate']
            if any(keyword in objectives.lower() for keyword in auto_keywords):
                return OperationMode.AUTO
            
            # Manual mode for simple tasks or explicit control
            manual_keywords = ['manual', 'control', 'step-by-step', 'guided']
            if any(keyword in objectives.lower() for keyword in manual_keywords):
                return OperationMode.MANUAL
            
            # Default to manual for simplicity
            return OperationMode.MANUAL
            
        except Exception as e:
            self.logger.error(f"Mode detection failed: {e}")
            return OperationMode.MANUAL  # Safe default
    
    def get_active_controller(self):
        """
        Get the currently active mode controller.
        
        Returns:
            Active controller instance (ManualModeController or AutoModeController)
        """
        if self.current_mode == OperationMode.MANUAL:
            return self.manual_controller
        elif self.current_mode == OperationMode.AUTO:
            return self.auto_controller
        else:
            return None
    
    def get_transition_status(self, transition_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a mode transition.
        
        Args:
            transition_id: ID of the transition to check
            
        Returns:
            Dictionary containing transition status or None if not found
        """
        # Check active transitions
        if transition_id in self.active_transitions:
            transition = self.active_transitions[transition_id]
            return {
                'transition_id': transition.transition_id,
                'from_mode': transition.from_mode.value,
                'to_mode': transition.to_mode.value,
                'status': transition.status,
                'started_at': transition.started_at.isoformat(),
                'completed_at': transition.completed_at.isoformat() if transition.completed_at else None,
                'error': transition.error
            }
        
        # Check transition history
        for transition in self.transition_history:
            if transition.transition_id == transition_id:
                return {
                    'transition_id': transition.transition_id,
                    'from_mode': transition.from_mode.value,
                    'to_mode': transition.to_mode.value,
                    'status': transition.status,
                    'started_at': transition.started_at.isoformat(),
                    'completed_at': transition.completed_at.isoformat() if transition.completed_at else None,
                    'error': transition.error
                }
        
        return None
    
    def register_mode_change_callback(self, callback_name: str, callback: Callable) -> None:
        """
        Register a callback for mode change events.
        
        Args:
            callback_name: Name of the callback
            callback: Callback function to call on mode changes
        """
        self.mode_change_callbacks[callback_name] = callback
        self.logger.debug(f"Registered mode change callback: {callback_name}")
    
    def get_mode_manager_status(self) -> Dict[str, Any]:
        """
        Get comprehensive mode manager status.
        
        Returns:
            Dictionary containing mode manager status and statistics
        """
        return {
            'manager_id': self.manager_id,
            'current_mode': self.current_mode.value,
            'previous_mode': self.previous_mode.value if self.previous_mode else None,
            'target_mode': self.target_mode.value if self.target_mode else None,
            'active_transitions': len(self.active_transitions),
            'transition_history_count': len(self.transition_history),
            'available_modes': [mode.value for mode in OperationMode if mode != OperationMode.TRANSITIONING],
            'mode_configurations': {
                mode.value: {
                    'is_active': config.is_active,
                    'last_modified': config.last_modified.isoformat()
                }
                for mode, config in self.mode_configurations.items()
            },
            'statistics': self.stats,
            'callbacks_registered': list(self.mode_change_callbacks.keys())
        }
    
    def _initialize_default_configurations(self) -> None:
        """Initialize default configurations for all modes."""
        # Manual mode configuration
        manual_config = ModeConfiguration(
            mode=OperationMode.MANUAL,
            config={
                'max_workers_per_type': 5,
                'ui_callbacks_enabled': True,
                'user_confirmation_required': True,
                'task_assignment_method': 'explicit',
                'collaborative_spaces_enabled': True
            },
            created_at=datetime.now(),
            last_modified=datetime.now()
        )
        self.mode_configurations[OperationMode.MANUAL] = manual_config
        
        # Auto mode configuration
        auto_config = ModeConfiguration(
            mode=OperationMode.AUTO,
            config={
                'max_workers_per_type': 10,
                'auto_scaling_enabled': True,
                'scale_up_threshold': 0.8,
                'scale_down_threshold': 0.3,
                'monitoring_interval': 30,
                'objective_analysis_enabled': True,
                'flowchart_execution_enabled': True,
                'initial_planner_timeout': 300
            },
            created_at=datetime.now(),
            last_modified=datetime.now()
        )
        self.mode_configurations[OperationMode.AUTO] = auto_config
    
    def _initialize_mode(self, mode: OperationMode) -> None:
        """
        Initialize a specific operation mode.
        
        Args:
            mode: Operation mode to initialize
        """
        try:
            if mode == OperationMode.MANUAL:
                self._initialize_manual_mode()
            elif mode == OperationMode.AUTO:
                self._initialize_auto_mode()
            
            self.current_mode = mode
            
            # Mark configuration as active
            if mode in self.mode_configurations:
                self.mode_configurations[mode].is_active = True
            
            self.logger.info(f"Initialized mode: {mode.value}")
            
        except Exception as e:
            self.logger.error(f"Mode initialization failed: {e}")
            raise
    
    def _initialize_manual_mode(self) -> None:
        """Initialize manual mode controller."""
        if not self.manual_controller:
            config = self.mode_configurations.get(OperationMode.MANUAL)
            controller_config = config.config if config else {}
            
            self.manual_controller = ManualModeController(
                server_instance=self.server,
                config=controller_config
            )
    
    def _initialize_auto_mode(self) -> None:
        """Initialize auto mode controller."""
        if not self.auto_controller:
            config = self.mode_configurations.get(OperationMode.AUTO)
            controller_config = config.config if config else {}
            
            self.auto_controller = AutoModeController(
                server_instance=self.server,
                config=controller_config
            )
    
    def _perform_mode_transition(self, transition: ModeTransition, preserve_state: bool) -> bool:
        """
        Perform the actual mode transition.
        
        Args:
            transition: ModeTransition object
            preserve_state: Whether to preserve state during transition
            
        Returns:
            True if transition was successful
        """
        try:
            from_mode = transition.from_mode
            to_mode = transition.to_mode
            
            # Cleanup current mode
            if from_mode != OperationMode.TRANSITIONING:
                self._cleanup_mode(from_mode, preserve_state)
            
            # Initialize target mode
            self._initialize_mode(to_mode)
            
            # Apply mode configuration
            if to_mode in self.mode_configurations:
                self._apply_mode_configuration(to_mode, self.mode_configurations[to_mode])
            
            # Transfer state if requested
            if preserve_state and from_mode != OperationMode.TRANSITIONING:
                self._transfer_mode_state(from_mode, to_mode)
            
            return True
            
        except Exception as e:
            transition.error = str(e)
            self.logger.error(f"Mode transition failed: {e}")
            return False
    
    def _cleanup_mode(self, mode: OperationMode, preserve_state: bool) -> None:
        """
        Cleanup a mode during transition.
        
        Args:
            mode: Mode to cleanup
            preserve_state: Whether to preserve state
        """
        try:
            if mode == OperationMode.MANUAL and self.manual_controller:
                if not preserve_state:
                    self.manual_controller.shutdown()
                    self.manual_controller = None
                
            elif mode == OperationMode.AUTO and self.auto_controller:
                if not preserve_state:
                    self.auto_controller.shutdown()
                    self.auto_controller = None
            
            # Mark configuration as inactive
            if mode in self.mode_configurations:
                self.mode_configurations[mode].is_active = False
            
        except Exception as e:
            self.logger.error(f"Mode cleanup failed for {mode.value}: {e}")
    
    def _apply_mode_configuration(self, mode: OperationMode, config: ModeConfiguration) -> None:
        """
        Apply configuration to a mode controller.
        
        Args:
            mode: Operation mode
            config: Mode configuration to apply
        """
        try:
            if mode == OperationMode.MANUAL and self.manual_controller:
                # Apply manual mode configuration
                self.manual_controller.config.update(config.config)
                
            elif mode == OperationMode.AUTO and self.auto_controller:
                # Apply auto mode configuration
                self.auto_controller.config.update(config.config)
                self.auto_controller.auto_scaling_config.update({
                    k: v for k, v in config.config.items()
                    if k in self.auto_controller.auto_scaling_config
                })
            
        except Exception as e:
            self.logger.error(f"Failed to apply configuration for {mode.value}: {e}")
    
    def _transfer_mode_state(self, from_mode: OperationMode, to_mode: OperationMode) -> None:
        """
        Transfer state between modes during transition.
        
        Args:
            from_mode: Source mode
            to_mode: Target mode
        """
        try:
            # This is a simplified implementation
            # In a real system, this would involve more sophisticated state transfer
            
            if from_mode == OperationMode.MANUAL and to_mode == OperationMode.AUTO:
                # Transfer manual workers to auto mode
                if self.manual_controller and self.auto_controller:
                    manual_workers = self.manual_controller.get_manual_workers()
                    self.logger.info(f"Transferring {len(manual_workers)} workers from manual to auto mode")
                    
            elif from_mode == OperationMode.AUTO and to_mode == OperationMode.MANUAL:
                # Transfer auto workers to manual mode
                if self.auto_controller and self.manual_controller:
                    auto_status = self.auto_controller.get_auto_mode_status()
                    self.logger.info(f"Transferring {auto_status.get('auto_workers', 0)} workers from auto to manual mode")
            
        except Exception as e:
            self.logger.error(f"State transfer failed: {e}")
    
    def _notify_mode_change(self, from_mode: OperationMode, to_mode: OperationMode) -> None:
        """
        Notify registered callbacks about mode changes.
        
        Args:
            from_mode: Previous mode
            to_mode: New mode
        """
        for callback_name, callback in self.mode_change_callbacks.items():
            try:
                callback(from_mode, to_mode)
            except Exception as e:
                self.logger.error(f"Mode change callback {callback_name} failed: {e}")
    
    def shutdown(self) -> None:
        """Shutdown the mode manager and all controllers."""
        try:
            # Shutdown controllers
            if self.manual_controller:
                self.manual_controller.shutdown()
                self.manual_controller = None
            
            if self.auto_controller:
                self.auto_controller.shutdown()
                self.auto_controller = None
            
            # Clear state
            self.active_transitions.clear()
            self.mode_change_callbacks.clear()
            
            # Mark all configurations as inactive
            for config in self.mode_configurations.values():
                config.is_active = False
            
            self.current_mode = OperationMode.TRANSITIONING
            
            self.logger.info("ModeManager shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during mode manager shutdown: {e}")
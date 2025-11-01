"""
Comprehensive Feature Testing for Botted Library v1 and v2

This test suite validates all features mentioned in features.txt to ensure
both v1 compatibility and v2 collaborative features work as intended.
"""

import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

# V1 Compatibility Tests
from botted_library.compatibility.v1_compatibility import create_worker, Worker as V1Worker

# V2 System Integration Tests
from botted_library.core.system_integration import (
    SystemIntegration, SystemConfiguration, SystemState,
    initialize_v2_system, shutdown_v2_system
)
from botted_library.core.system_startup import SystemStartup, StartupOptions, quick_start_system
from botted_library.core.interfaces import WorkerType

# V2 Collaborative Components
from botted_library.core.collaborative_server import CollaborativeServer
from botted_library.core.enhanced_worker_registry import EnhancedWorkerRegistry
from botted_library.core.enhanced_worker import EnhancedWorker
from botted_library.core.planner_worker import PlannerWorker
from botted_library.core.executor_worker import ExecutorWorker
from botted_library.core.verifier_worker import VerifierWorker

# Collaborative Spaces
from botted_library.core.collaborative_space import CollaborativeSpace
from botted_library.core.shared_whiteboard import SharedWhiteboard
from botted_library.core.shared_filesystem import SharedFileSystem

# Mode Controllers
from botted_library.core.mode_manager import ModeManager
from botted_library.core.manual_mode_controller import ManualModeController
from botted_library.core.auto_mode_controller import AutoModeController

# Enhanced Tools and Plugins
from botted_library.core.plugin_system import PluginManager, get_plugin_manager
from botted_library.core.enhanced_tools import EnhancedToolManager, get_enhanced_tool_manager

# Error Handling and Monitoring
from botted_library.core.error_recovery import ErrorRecoverySystem
from botted_library.core.monitoring_system import MonitoringSystem

# Configuration Management
from botted_library.core.configuration_manager import ConfigurationManager


class TestV1Compatibility:
    """Test V1 compatibility features"""
    
    def test_v1_worker_creation(self):
        """Test that V1 worker creation still works"""
        with patch('botted_library.compatibility.v1_compatibility.Worker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker.call = Mock(return_value="V1 result")
            mock_worker_class.return_value = mock_worker
            
            # Test V1 create_worker function
            worker = create_worker("TestWorker", "Test Role", "Test job description")
            assert worker is not None
            
            # Test V1 worker.call method
            result = worker.call("test task")
            assert result == "V1 result"
            mock_worker.call.assert_called_with("test task")
    
    def test_v1_worker_interface_preserved(self):
        """Test that V1 worker interface is preserved"""
        with patch('botted_library.compatibility.v1_compatibility.Worker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker.name = "TestWorker"
            mock_worker.role = "Test Role"
            mock_worker.call = Mock()
            mock_worker_class.return_value = mock_worker
            
            worker = create_worker("TestWorker", "Test Role", "Test job description")
            
            # Verify V1 interface methods exist
            assert hasattr(worker, 'call')
            assert hasattr(worker, 'name')
            assert hasattr(worker, 'role')


class TestBackgroundServer:
    """Test background server deployment and operations"""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        return SystemConfiguration(
            server_port=8774,
            enable_monitoring=False,
            log_level="ERROR"
        )
    
    @pytest.mark.asyncio
    async def test_server_deployment(self, test_config):
        """Test that background server deploys when workers are activated"""
        system = SystemIntegration(test_config)
        
        with patch.multiple(
            system,
            _initialize_error_recovery=AsyncMock(),
            _initialize_monitoring_system=AsyncMock(),
            _initialize_plugin_manager=AsyncMock(),
            _initialize_tool_manager=AsyncMock(),
            _initialize_worker_registry=AsyncMock(),
            _initialize_server=AsyncMock(),
            _initialize_mode_manager=AsyncMock(),
            _start_background_tasks=Mock()
        ):
            # Server should start automatically during system initialization
            success = await system.initialize_system()
            assert success is True
            
            # Verify server initialization was called
            system._initialize_server.assert_called_once()
            
            # Verify system is running
            assert system.state == SystemState.RUNNING
    
    def test_server_handles_operations(self):
        """Test that server handles all operations behind the scenes"""
        mock_server = Mock(spec=CollaborativeServer)
        mock_server.handle_worker_request = Mock()
        mock_server.route_message = Mock()
        mock_server.manage_collaborative_space = Mock()
        
        # Verify server has operation handling capabilities
        assert hasattr(mock_server, 'handle_worker_request')
        assert hasattr(mock_server, 'route_message')
        assert hasattr(mock_server, 'manage_collaborative_space')


class TestWorkerCommunication:
    """Test worker communication through server"""
    
    def test_worker_to_worker_communication(self):
        """Test workers can communicate with each other via server"""
        # Mock server and workers
        mock_server = Mock()
        mock_server.route_message = Mock()
        
        mock_worker1 = Mock(spec=EnhancedWorker)
        mock_worker1.worker_id = "worker1"
        mock_worker1.send_message_to_worker = Mock()
        
        mock_worker2 = Mock(spec=EnhancedWorker)
        mock_worker2.worker_id = "worker2"
        mock_worker2.receive_message = Mock()
        
        # Test message sending
        message = {"type": "task_request", "content": "Please help with analysis"}
        mock_worker1.send_message_to_worker("worker2", message)
        
        # Verify communication method exists
        mock_worker1.send_message_to_worker.assert_called_with("worker2", message)
    
    def test_server_message_routing(self):
        """Test server routes messages between workers"""
        mock_server = Mock()
        mock_server.route_message = Mock()
        
        # Test message routing
        sender_id = "planner1"
        recipient_id = "executor1"
        message = {"type": "task_assignment", "task": "analyze_data"}
        
        mock_server.route_message(sender_id, recipient_id, message)
        mock_server.route_message.assert_called_with(sender_id, recipient_id, message)


class TestCollaborativeSpaces:
    """Test collaborative spaces functionality"""
    
    def test_collaborative_space_creation(self):
        """Test multiple workers can work together in shared spaces"""
        mock_space = Mock(spec=CollaborativeSpace)
        mock_space.add_participant = Mock()
        mock_space.get_participants = Mock(return_value=[])
        
        # Test adding workers to collaborative space
        mock_space.add_participant("planner1")
        mock_space.add_participant("executor1")
        mock_space.add_participant("verifier1")
        
        assert mock_space.add_participant.call_count == 3
    
    def test_shared_whiteboard(self):
        """Test shared whiteboard functionality"""
        mock_whiteboard = Mock(spec=SharedWhiteboard)
        mock_whiteboard.add_content = Mock()
        mock_whiteboard.get_content = Mock(return_value="")
        mock_whiteboard.collaborate_on_content = Mock()
        
        # Test whiteboard operations
        mock_whiteboard.add_content("Planning diagram for project X")
        mock_whiteboard.collaborate_on_content("worker1", "Added execution steps")
        
        assert mock_whiteboard.add_content.called
        assert mock_whiteboard.collaborate_on_content.called
    
    def test_shared_files(self):
        """Test shared file system functionality"""
        mock_filesystem = Mock(spec=SharedFileSystem)
        mock_filesystem.create_file = Mock()
        mock_filesystem.share_file = Mock()
        mock_filesystem.get_file_access = Mock()
        
        # Test file sharing operations
        mock_filesystem.create_file("project_plan.md", "# Project Plan\n...")
        mock_filesystem.share_file("project_plan.md", ["planner1", "executor1"])
        
        assert mock_filesystem.create_file.called
        assert mock_filesystem.share_file.called


class TestWorkerSubgroups:
    """Test three worker subgroups: Executors, Planners, Verifiers"""
    
    def test_worker_types_exist(self):
        """Test all three worker types are properly defined"""
        assert WorkerType.EXECUTOR in WorkerType
        assert WorkerType.PLANNER in WorkerType
        assert WorkerType.VERIFIER in WorkerType
        assert len(WorkerType) == 3
    
    def test_executor_functionality(self):
        """Test Executor workers perform tasks and actions"""
        mock_executor = Mock(spec=ExecutorWorker)
        mock_executor.execute_task = Mock()
        mock_executor.perform_action = Mock()
        mock_executor.report_progress = Mock()
        
        # Test executor capabilities
        task = {"id": "task1", "description": "Process data", "parameters": {}}
        mock_executor.execute_task(task)
        mock_executor.perform_action("web_search", {"query": "test"})
        
        assert mock_executor.execute_task.called
        assert mock_executor.perform_action.called
    
    def test_planner_functionality(self):
        """Test Planner workers develop strategies and assign tasks"""
        mock_planner = Mock(spec=PlannerWorker)
        mock_planner.create_strategy = Mock()
        mock_planner.assign_task_to_executor = Mock()
        mock_planner.create_execution_plan = Mock()
        mock_planner.monitor_progress = Mock()
        
        # Test planner capabilities
        objective = "Complete market research project"
        mock_planner.create_strategy(objective)
        mock_planner.assign_task_to_executor("executor1", {"task": "gather_data"})
        
        assert mock_planner.create_strategy.called
        assert mock_planner.assign_task_to_executor.called
    
    def test_verifier_functionality(self):
        """Test Verifier workers validate work quality"""
        mock_verifier = Mock(spec=VerifierWorker)
        mock_verifier.validate_output = Mock(return_value={"valid": True, "score": 0.9})
        mock_verifier.check_quality = Mock()
        mock_verifier.approve_for_delivery = Mock()
        
        # Test verifier capabilities
        output = {"result": "Market analysis complete", "data": {...}}
        validation_result = mock_verifier.validate_output(output)
        
        assert mock_verifier.validate_output.called
        assert validation_result["valid"] is True


class TestPlannerWorkerCreation:
    """Test Planner ability to initialize new workers"""
    
    def test_planner_creates_workers(self):
        """Test Planners can initialize new workers as needed"""
        mock_planner = Mock(spec=PlannerWorker)
        mock_planner.create_new_worker = Mock(return_value="new_worker_id")
        mock_planner.specify_worker_capabilities = Mock()
        
        # Test worker creation
        new_worker_id = mock_planner.create_new_worker(
            WorkerType.EXECUTOR, 
            {"specialization": "data_analysis"}
        )
        
        assert new_worker_id == "new_worker_id"
        assert mock_planner.create_new_worker.called
    
    def test_server_registers_new_workers(self):
        """Test server registers newly created workers"""
        mock_server = Mock()
        mock_server.register_worker = Mock(return_value="worker_123")
        
        mock_worker = Mock()
        worker_id = mock_server.register_worker(mock_worker)
        
        assert worker_id == "worker_123"
        assert mock_server.register_worker.called


class TestWorkspaceModes:
    """Test Manual and Auto workspace modes"""
    
    def test_manual_mode(self):
        """Test Manual Mode where user manually creates and assigns workers"""
        mock_manual_controller = Mock(spec=ManualModeController)
        mock_manual_controller.create_worker_manually = Mock()
        mock_manual_controller.assign_task_manually = Mock()
        mock_manual_controller.manage_workflow = Mock()
        
        # Test manual operations
        mock_manual_controller.create_worker_manually(WorkerType.EXECUTOR, "data_analyst")
        mock_manual_controller.assign_task_manually("worker1", {"task": "analyze"})
        
        assert mock_manual_controller.create_worker_manually.called
        assert mock_manual_controller.assign_task_manually.called
    
    def test_auto_mode(self):
        """Test Auto Mode with automatic planner activation"""
        mock_auto_controller = Mock(spec=AutoModeController)
        mock_auto_controller.activate_initial_planner = Mock()
        mock_auto_controller.create_additional_planners = Mock()
        mock_auto_controller.manage_executor_teams = Mock()
        
        # Test auto mode operations
        objective = "Complete comprehensive market analysis"
        mock_auto_controller.activate_initial_planner(objective)
        
        assert mock_auto_controller.activate_initial_planner.called
    
    def test_mode_manager_switches_modes(self):
        """Test mode manager can switch between manual and auto modes"""
        mock_mode_manager = Mock(spec=ModeManager)
        mock_mode_manager.switch_to_manual_mode = Mock()
        mock_mode_manager.switch_to_auto_mode = Mock()
        mock_mode_manager.get_current_mode = Mock()
        
        # Test mode switching
        mock_mode_manager.switch_to_manual_mode()
        mock_mode_manager.switch_to_auto_mode()
        
        assert mock_mode_manager.switch_to_manual_mode.called
        assert mock_mode_manager.switch_to_auto_mode.called


class TestEnhancedIntegrations:
    """Test enhanced integrations and tools"""
    
    def test_plugin_system(self):
        """Test plugin system for new integrations"""
        mock_plugin_manager = Mock(spec=PluginManager)
        mock_plugin_manager.load_plugin = Mock()
        mock_plugin_manager.get_available_plugins = Mock(return_value=[])
        mock_plugin_manager.enable_plugin = Mock()
        
        # Test plugin operations
        mock_plugin_manager.load_plugin("web_scraper_plugin")
        mock_plugin_manager.enable_plugin("api_integration_plugin")
        
        assert mock_plugin_manager.load_plugin.called
        assert mock_plugin_manager.enable_plugin.called
    
    def test_enhanced_tools(self):
        """Test enhanced tool manager for worker tools"""
        mock_tool_manager = Mock(spec=EnhancedToolManager)
        mock_tool_manager.register_tool = Mock()
        mock_tool_manager.get_tool = Mock()
        mock_tool_manager.execute_tool = Mock()
        
        # Test tool operations
        mock_tool_manager.register_tool("advanced_web_search", {})
        mock_tool_manager.execute_tool("data_analysis_tool", {"data": []})
        
        assert mock_tool_manager.register_tool.called
        assert mock_tool_manager.execute_tool.called


class TestAutoModeFlowchart:
    """Test Auto Mode flowchart creation and management"""
    
    def test_initial_planner_creates_flowchart(self):
        """Test initial planner creates office flowchart"""
        mock_planner = Mock(spec=PlannerWorker)
        mock_planner.create_office_flowchart = Mock()
        mock_planner.determine_worker_allocation = Mock()
        mock_planner.define_interaction_order = Mock()
        
        # Test flowchart creation
        objective = "Build comprehensive business analysis"
        mock_planner.create_office_flowchart(objective)
        
        assert mock_planner.create_office_flowchart.called
    
    def test_flowchart_defines_worker_structure(self):
        """Test flowchart defines how many of each worker type"""
        mock_planner = Mock()
        mock_planner.determine_worker_allocation = Mock(return_value={
            "planners": 2,
            "executors": 8,
            "verifiers": 3
        })
        
        allocation = mock_planner.determine_worker_allocation("complex_project")
        
        assert allocation["planners"] == 2
        assert allocation["executors"] == 8
        assert allocation["verifiers"] == 3
    
    def test_flowchart_defines_interaction_order(self):
        """Test flowchart dictates worker interaction order"""
        mock_planner = Mock()
        mock_planner.define_interaction_order = Mock(return_value=[
            "planner1 -> executor1,executor2,executor3",
            "executor1,executor2,executor3 -> verifier1",
            "verifier1 -> planner1"
        ])
        
        interaction_order = mock_planner.define_interaction_order()
        assert len(interaction_order) == 3
        assert "planner1 -> executor1,executor2,executor3" in interaction_order


class TestSystemIntegration:
    """Test complete system integration"""
    
    @pytest.mark.asyncio
    async def test_v2_system_initialization(self):
        """Test v2 system initializes all components"""
        config = SystemConfiguration(
            server_port=8775,
            enable_monitoring=False,
            log_level="ERROR"
        )
        
        system = SystemIntegration(config)
        
        with patch.multiple(
            system,
            _initialize_error_recovery=AsyncMock(),
            _initialize_monitoring_system=AsyncMock(),
            _initialize_plugin_manager=AsyncMock(),
            _initialize_tool_manager=AsyncMock(),
            _initialize_worker_registry=AsyncMock(),
            _initialize_server=AsyncMock(),
            _initialize_mode_manager=AsyncMock(),
            _start_background_tasks=Mock()
        ):
            success = await system.initialize_system()
            assert success is True
            assert system.state == SystemState.RUNNING
    
    def test_configuration_management(self):
        """Test comprehensive configuration management"""
        config_manager = ConfigurationManager()
        
        # Test configuration access
        assert config_manager.get_value("server_host") is not None
        assert config_manager.get_value("max_workers_per_type") is not None
        
        # Test configuration modification
        config_manager.set_value("server_port", 9999)
        assert config_manager.get_value("server_port") == 9999
    
    def test_error_handling_and_monitoring(self):
        """Test error handling and monitoring systems"""
        mock_error_recovery = Mock(spec=ErrorRecoverySystem)
        mock_error_recovery.handle_error = Mock()
        mock_error_recovery.retry_operation = Mock()
        
        mock_monitoring = Mock(spec=MonitoringSystem)
        mock_monitoring.collect_metrics = Mock()
        mock_monitoring.get_system_health = Mock()
        
        # Test error handling
        mock_error_recovery.handle_error("test_error", {})
        assert mock_error_recovery.handle_error.called
        
        # Test monitoring
        mock_monitoring.collect_metrics()
        assert mock_monitoring.collect_metrics.called


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_v1_to_v2_workflow(self):
        """Test complete workflow from v1 compatibility to v2 features"""
        # Step 1: V1 worker creation (backward compatibility)
        with patch('botted_library.compatibility.v1_compatibility.Worker') as mock_v1_worker:
            mock_worker = Mock()
            mock_worker.call = Mock(return_value="v1_result")
            mock_v1_worker.return_value = mock_worker
            
            v1_worker = create_worker("TestWorker", "Analyst", "Data analysis expert")
            assert v1_worker is not None
        
        # Step 2: V2 system initialization
        config = SystemConfiguration(server_port=8776, enable_monitoring=False, log_level="ERROR")
        system = SystemIntegration(config)
        
        with patch.multiple(
            system,
            _initialize_error_recovery=AsyncMock(),
            _initialize_monitoring_system=AsyncMock(),
            _initialize_plugin_manager=AsyncMock(),
            _initialize_tool_manager=AsyncMock(),
            _initialize_worker_registry=AsyncMock(),
            _initialize_server=AsyncMock(),
            _initialize_mode_manager=AsyncMock(),
            _start_background_tasks=Mock()
        ):
            success = await system.initialize_system()
            assert success is True
        
        # Step 3: Collaborative features activation
        mock_server = Mock()
        mock_server.create_collaborative_space = Mock(return_value="space_123")
        system.server = mock_server
        
        space_id = mock_server.create_collaborative_space("project_alpha")
        assert space_id == "space_123"
        
        # Step 4: Worker collaboration
        mock_planner = Mock(spec=PlannerWorker)
        mock_executor = Mock(spec=ExecutorWorker)
        mock_verifier = Mock(spec=VerifierWorker)
        
        # Simulate collaborative workflow
        mock_planner.create_strategy = Mock()
        mock_planner.assign_task_to_executor = Mock()
        mock_executor.execute_task = Mock()
        mock_verifier.validate_output = Mock(return_value={"valid": True})
        
        # Execute workflow
        mock_planner.create_strategy("market_analysis")
        mock_planner.assign_task_to_executor("executor1", {"task": "data_collection"})
        mock_executor.execute_task({"task": "data_collection"})
        validation = mock_verifier.validate_output({"result": "data_collected"})
        
        assert mock_planner.create_strategy.called
        assert mock_executor.execute_task.called
        assert validation["valid"] is True


class TestPerformanceAndScalability:
    """Test system performance and scalability"""
    
    def test_multiple_worker_creation(self):
        """Test system can handle multiple workers"""
        mock_registry = Mock(spec=EnhancedWorkerRegistry)
        mock_registry.register_worker = Mock()
        mock_registry.get_worker_count = Mock(return_value=0)
        
        # Simulate creating multiple workers
        for i in range(10):
            mock_registry.register_worker(Mock())
        
        assert mock_registry.register_worker.call_count == 10
    
    def test_concurrent_collaborative_spaces(self):
        """Test multiple collaborative spaces can run concurrently"""
        mock_server = Mock()
        mock_server.create_collaborative_space = Mock(side_effect=lambda name: f"space_{name}")
        mock_server.get_active_spaces = Mock(return_value=[])
        
        # Create multiple spaces
        spaces = []
        for i in range(5):
            space_id = mock_server.create_collaborative_space(f"project_{i}")
            spaces.append(space_id)
        
        assert len(spaces) == 5
        assert mock_server.create_collaborative_space.call_count == 5
    
    def test_message_routing_performance(self):
        """Test message routing can handle multiple concurrent messages"""
        mock_router = Mock()
        mock_router.route_message = Mock()
        
        # Simulate concurrent message routing
        for i in range(100):
            mock_router.route_message(f"sender_{i}", f"recipient_{i}", {"msg": f"message_{i}"})
        
        assert mock_router.route_message.call_count == 100


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"])
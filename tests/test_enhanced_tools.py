"""
Unit tests for Enhanced Tools and Plugin System

Tests the plugin architecture, enhanced tools, and tool optimization system.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from botted_library.core.plugin_system import (
    PluginRegistry, PluginManager, PluginDiscovery, IPlugin,
    PluginStatus, PluginCapability, PluginMetadata
)
from botted_library.core.enhanced_tools import (
    EnhancedToolManager, WebScrapingTool, DataAnalysisTool, 
    DocumentProcessingTool, IEnhancedTool
)
from botted_library.core.advanced_integrations import (
    CollaborativeCommunicationTool, AdvancedAutomationTool, EnhancedBrowserTool
)
from botted_library.core.tool_optimization import (
    ToolUsageTracker, ToolOptimizer, ToolUsageMetrics, OptimizationRecommendation
)
from botted_library.core.exceptions import WorkerError


class TestPluginRegistry(unittest.TestCase):
    """Test cases for PluginRegistry"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.registry = PluginRegistry()
        self.mock_plugin = Mock(spec=IPlugin)
        self.mock_plugin.get_metadata.return_value = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            capabilities=[
                PluginCapability(
                    name="test_capability",
                    description="Test capability",
                    input_types=["text"],
                    output_types=["result"],
                    requirements={}
                )
            ],
            dependencies=[],
            collaborative_features={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.mock_plugin.supports_collaboration.return_value = False
    
    def test_registry_initialization(self):
        """Test registry initialization"""
        self.assertEqual(len(self.registry._plugins), 0)
        self.assertEqual(len(self.registry._plugin_status), 0)
        self.assertEqual(len(self.registry._capability_map), 0)
    
    def test_register_plugin_success(self):
        """Test successful plugin registration"""
        result = self.registry.register_plugin(self.mock_plugin)
        
        self.assertTrue(result)
        self.assertIn("test_plugin", self.registry._plugins)
        self.assertEqual(self.registry._plugin_status["test_plugin"], PluginStatus.LOADED)
        self.assertIn("test_capability", self.registry._capability_map)
        self.assertEqual(self.registry._capability_map["test_capability"], "test_plugin")
    
    def test_register_plugin_duplicate_name(self):
        """Test registering plugin with duplicate name"""
        # Register first plugin
        self.registry.register_plugin(self.mock_plugin)
        
        # Register second plugin with same name
        mock_plugin2 = Mock(spec=IPlugin)
        mock_plugin2.get_metadata.return_value = self.mock_plugin.get_metadata.return_value
        mock_plugin2.supports_collaboration.return_value = False
        
        result = self.registry.register_plugin(mock_plugin2)
        self.assertTrue(result)  # Should succeed but replace existing
        self.assertEqual(self.registry._plugins["test_plugin"], mock_plugin2)
    
    def test_unregister_plugin_success(self):
        """Test successful plugin unregistration"""
        # Register plugin first
        self.registry.register_plugin(self.mock_plugin)
        
        # Unregister plugin
        result = self.registry.unregister_plugin("test_plugin")
        
        self.assertTrue(result)
        self.assertNotIn("test_plugin", self.registry._plugins)
        self.assertNotIn("test_plugin", self.registry._plugin_status)
        self.assertNotIn("test_capability", self.registry._capability_map)
    
    def test_unregister_nonexistent_plugin(self):
        """Test unregistering non-existent plugin"""
        result = self.registry.unregister_plugin("nonexistent_plugin")
        self.assertFalse(result)
    
    def test_get_plugin_by_capability(self):
        """Test getting plugin by capability"""
        self.registry.register_plugin(self.mock_plugin)
        
        plugin = self.registry.get_plugin_by_capability("test_capability")
        self.assertEqual(plugin, self.mock_plugin)
        
        plugin = self.registry.get_plugin_by_capability("nonexistent_capability")
        self.assertIsNone(plugin)
    
    def test_collaborative_plugin_tracking(self):
        """Test tracking of collaborative plugins"""
        # Register non-collaborative plugin
        self.registry.register_plugin(self.mock_plugin)
        self.assertEqual(len(self.registry.get_collaborative_plugins()), 0)
        
        # Register collaborative plugin
        collab_plugin = Mock(spec=IPlugin)
        collab_plugin.get_metadata.return_value = PluginMetadata(
            name="collab_plugin",
            version="1.0.0",
            description="Collaborative plugin",
            author="Test Author",
            capabilities=[],
            dependencies=[],
            collaborative_features={"sharing": True},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        collab_plugin.supports_collaboration.return_value = True
        
        self.registry.register_plugin(collab_plugin)
        self.assertEqual(len(self.registry.get_collaborative_plugins()), 1)
        self.assertIn("collab_plugin", self.registry.get_collaborative_plugins())


class TestPluginManager(unittest.TestCase):
    """Test cases for PluginManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.registry = PluginRegistry()
        self.manager = PluginManager(self.registry)
        
        # Create mock plugin
        self.mock_plugin = Mock(spec=IPlugin)
        self.mock_plugin.get_metadata.return_value = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            capabilities=[
                PluginCapability(
                    name="test_capability",
                    description="Test capability",
                    input_types=["text"],
                    output_types=["result"],
                    requirements={}
                )
            ],
            dependencies=[],
            collaborative_features={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.mock_plugin.initialize.return_value = True
        self.mock_plugin.execute.return_value = {"success": True, "result": "test_result"}
        self.mock_plugin.supports_collaboration.return_value = False
        
        # Register plugin
        self.registry.register_plugin(self.mock_plugin)
    
    def test_initialize_plugin_success(self):
        """Test successful plugin initialization"""
        result = self.manager.initialize_plugin("test_plugin", {"config": "value"})
        
        self.assertTrue(result)
        self.mock_plugin.initialize.assert_called_once_with({"config": "value"})
        self.assertEqual(self.registry.get_plugin_status("test_plugin"), PluginStatus.ACTIVE)
    
    def test_initialize_plugin_failure(self):
        """Test plugin initialization failure"""
        self.mock_plugin.initialize.return_value = False
        
        result = self.manager.initialize_plugin("test_plugin", {})
        
        self.assertFalse(result)
        self.assertEqual(self.registry.get_plugin_status("test_plugin"), PluginStatus.ERROR)
    
    def test_execute_capability_success(self):
        """Test successful capability execution"""
        # Initialize plugin first
        self.manager.initialize_plugin("test_plugin", {})
        
        result = self.manager.execute_capability(
            "test_capability", 
            {"input": "test"}, 
            {"context": "test"}
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], "test_result")
        self.assertIn("_plugin_metadata", result)
        self.mock_plugin.execute.assert_called_once()
    
    def test_execute_capability_plugin_not_found(self):
        """Test executing capability with non-existent plugin"""
        with self.assertRaises(WorkerError):
            self.manager.execute_capability("nonexistent_capability", {}, {})
    
    def test_execute_capability_plugin_not_active(self):
        """Test executing capability with inactive plugin"""
        # Don't initialize plugin (it should be in LOADED state)
        with self.assertRaises(WorkerError):
            self.manager.execute_capability("test_capability", {}, {})
    
    def test_usage_statistics_tracking(self):
        """Test usage statistics tracking"""
        # Initialize and execute capability
        self.manager.initialize_plugin("test_plugin", {})
        self.manager.execute_capability("test_capability", {}, {})
        
        stats = self.manager.get_usage_statistics()
        self.assertIn("test_plugin", stats)
        self.assertEqual(stats["test_plugin"]["total_executions"], 1)
        self.assertIn("test_capability", stats["test_plugin"]["capabilities_used"])


class TestEnhancedTools(unittest.TestCase):
    """Test cases for Enhanced Tools"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.web_scraping_tool = WebScrapingTool()
        self.data_analysis_tool = DataAnalysisTool()
        self.document_processing_tool = DocumentProcessingTool()
    
    def test_web_scraping_tool_initialization(self):
        """Test web scraping tool initialization"""
        result = self.web_scraping_tool.initialize({"enable_cache": True})
        self.assertTrue(result)
        self.assertTrue(self.web_scraping_tool._initialized)
        self.assertTrue(self.web_scraping_tool.cache_enabled)
    
    def test_web_scraping_tool_metadata(self):
        """Test web scraping tool metadata"""
        metadata = self.web_scraping_tool.get_metadata()
        self.assertEqual(metadata.name, "enhanced_web_scraping")
        self.assertEqual(len(metadata.capabilities), 2)
        self.assertTrue(metadata.collaborative_features["shared_cache"])
    
    def test_web_scraping_tool_execution(self):
        """Test web scraping tool execution"""
        self.web_scraping_tool.initialize({})
        
        result = self.web_scraping_tool.execute(
            "scrape_website",
            {"url": "https://example.com", "selectors": {"title": "h1"}},
            {}
        )
        
        self.assertTrue(result["success"])
        self.assertIn("data", result)
        self.assertEqual(result["data"]["url"], "https://example.com")
    
    def test_web_scraping_tool_collaborative_execution(self):
        """Test web scraping tool collaborative execution"""
        self.web_scraping_tool.initialize({})
        
        result = self.web_scraping_tool.execute_collaborative(
            "scrape_website",
            {"url": "https://example.com", "selectors": {"title": "h1"}},
            {"participant_workers": ["worker1", "worker2"]}
        )
        
        self.assertTrue(result["success"])
        self.assertIn("collaborative_metadata", result)
        self.assertEqual(len(result["collaborative_metadata"]["shared_with_workers"]), 2)
    
    def test_data_analysis_tool_execution(self):
        """Test data analysis tool execution"""
        self.data_analysis_tool.initialize({})
        
        result = self.data_analysis_tool.execute(
            "analyze_dataset",
            {"data": [1, 2, 3, 4, 5], "analysis_type": "descriptive"},
            {}
        )
        
        self.assertTrue(result["success"])
        self.assertIn("analysis_results", result)
        self.assertEqual(result["analysis_results"]["analysis_type"], "descriptive")
    
    def test_document_processing_tool_execution(self):
        """Test document processing tool execution"""
        self.document_processing_tool.initialize({})
        
        result = self.document_processing_tool.execute(
            "process_document",
            {"document": "Test document content", "processing_type": "extract_metadata"},
            {}
        )
        
        self.assertTrue(result["success"])
        self.assertIn("processed_document", result)
        self.assertIn("document_metadata", result["processed_document"])
    
    def test_tool_worker_type_support(self):
        """Test tool worker type support"""
        self.assertTrue(self.web_scraping_tool.supports_worker_type("executor"))
        self.assertTrue(self.web_scraping_tool.supports_worker_type("planner"))
        self.assertFalse(self.web_scraping_tool.supports_worker_type("invalid_type"))
    
    def test_tool_shared_resources(self):
        """Test tool shared resources"""
        resources = self.web_scraping_tool.get_shared_resources()
        self.assertIn("scraping_cache", resources)
        self.assertIn("extracted_data", resources)


class TestAdvancedIntegrations(unittest.TestCase):
    """Test cases for Advanced Integrations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.communication_tool = CollaborativeCommunicationTool()
        self.automation_tool = AdvancedAutomationTool()
        self.browser_tool = EnhancedBrowserTool()
    
    def test_communication_tool_initialization(self):
        """Test communication tool initialization"""
        result = self.communication_tool.initialize({
            "enable_message_persistence": True,
            "max_message_history": 500
        })
        self.assertTrue(result)
        self.assertTrue(self.communication_tool.message_persistence)
        self.assertEqual(self.communication_tool.max_message_history, 500)
    
    def test_communication_tool_send_message(self):
        """Test sending messages"""
        self.communication_tool.initialize({})
        
        result = self.communication_tool.execute(
            "send_message",
            {
                "recipient": "worker2",
                "message": "Hello from worker1",
                "message_type": "text"
            },
            {"worker_id": "worker1"}
        )
        
        self.assertTrue(result["success"])
        self.assertIn("delivery_result", result)
        self.assertEqual(result["delivery_result"]["recipient"], "worker2")
        self.assertEqual(result["delivery_result"]["delivery_status"], "delivered")
    
    def test_automation_tool_create_workflow(self):
        """Test workflow creation"""
        self.automation_tool.initialize({})
        
        result = self.automation_tool.execute(
            "create_workflow",
            {
                "workflow_name": "Test Workflow",
                "steps": [
                    {"name": "Step 1", "estimated_time": 30},
                    {"name": "Step 2", "estimated_time": 45}
                ],
                "triggers": ["manual"]
            },
            {"worker_id": "planner1"}
        )
        
        self.assertTrue(result["success"])
        self.assertIn("workflow_definition", result)
        self.assertEqual(result["workflow_definition"]["workflow_name"], "Test Workflow")
        self.assertIn("execution_plan", result)
        self.assertEqual(result["execution_plan"]["total_steps"], 2)
    
    def test_browser_tool_collaborative_browsing(self):
        """Test collaborative browsing"""
        self.browser_tool.initialize({})
        
        result = self.browser_tool.execute(
            "collaborative_browsing",
            {
                "url": "https://example.com",
                "session_name": "test_session"
            },
            {"worker_id": "executor1", "participant_workers": ["executor1", "executor2"]}
        )
        
        self.assertTrue(result["success"])
        self.assertIn("shared_session", result)
        self.assertEqual(result["shared_session"]["url"], "https://example.com")
        self.assertEqual(len(result["shared_session"]["participants"]), 2)


class TestToolOptimization(unittest.TestCase):
    """Test cases for Tool Optimization System"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.usage_tracker = ToolUsageTracker()
        self.optimizer = ToolOptimizer(self.usage_tracker)
    
    def test_usage_tracking(self):
        """Test usage tracking functionality"""
        # Record some usage events
        self.usage_tracker.record_usage(
            "test_tool", "test_capability", 2.5, True, False, "executor", 0.85
        )
        self.usage_tracker.record_usage(
            "test_tool", "test_capability", 3.0, True, True, "executor", 0.90
        )
        
        # Get metrics
        metrics = self.usage_tracker.get_tool_metrics("test_tool")
        
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.tool_name, "test_tool")
        self.assertEqual(metrics.usage_count, 2)
        self.assertEqual(metrics.success_rate, 1.0)
        self.assertEqual(metrics.collaborative_usage_count, 1)
        self.assertAlmostEqual(metrics.average_execution_time, 2.75)
    
    def test_performance_analysis(self):
        """Test performance analysis"""
        # Record usage for multiple tools
        self.usage_tracker.record_usage("fast_tool", "capability1", 1.0, True, False, "executor", 0.95)
        self.usage_tracker.record_usage("slow_tool", "capability1", 65.0, True, False, "executor", 0.60)
        self.usage_tracker.record_usage("unreliable_tool", "capability1", 2.0, False, False, "executor", 0.30)
        
        analysis = self.optimizer.analyze_performance()
        
        self.assertIn("performance_summary", analysis)
        self.assertIn("bottlenecks", analysis)
        self.assertIn("high_performing_tools", analysis)
        
        # Check that slow and unreliable tools are identified as bottlenecks
        bottleneck_tools = [b["tool_name"] for b in analysis["bottlenecks"]]
        self.assertIn("slow_tool", bottleneck_tools)
        self.assertIn("unreliable_tool", bottleneck_tools)
        
        # Check that fast tool is identified as high performing
        self.assertIn("fast_tool", analysis["high_performing_tools"])
    
    def test_optimization_recommendations(self):
        """Test optimization recommendations generation"""
        # Record problematic usage patterns
        self.usage_tracker.record_usage("slow_tool", "capability1", 70.0, True, False, "executor", 0.60)
        self.usage_tracker.record_usage("unreliable_tool", "capability1", 2.0, False, False, "executor", 0.30)
        
        recommendations = self.optimizer.generate_recommendations()
        
        self.assertGreater(len(recommendations), 0)
        
        # Check recommendation types
        rec_types = [rec.recommendation_type for rec in recommendations]
        self.assertIn("performance", rec_types)
        self.assertIn("reliability", rec_types)
        
        # Check that high priority recommendations exist
        high_priority_recs = [rec for rec in recommendations if rec.implementation_priority == "high"]
        self.assertGreater(len(high_priority_recs), 0)
    
    def test_tool_selection_optimization(self):
        """Test optimal tool selection"""
        # Record usage for different tools
        self.usage_tracker.record_usage("excellent_tool", "capability1", 1.5, True, True, "executor", 0.95)
        self.usage_tracker.record_usage("good_tool", "capability1", 2.0, True, False, "executor", 0.80)
        self.usage_tracker.record_usage("poor_tool", "capability1", 10.0, False, False, "executor", 0.40)
        
        recommendations = self.optimizer.optimize_tool_selection(
            ["capability1"], 
            worker_type="executor", 
            collaborative=True
        )
        
        self.assertGreater(len(recommendations), 0)
        
        # Check that excellent_tool is recommended first
        top_recommendation = recommendations[0]
        self.assertEqual(top_recommendation[0], "excellent_tool")
        self.assertGreater(top_recommendation[1], 0.8)  # High score
    
    def test_optimization_report_generation(self):
        """Test comprehensive optimization report generation"""
        # Record some usage data
        self.usage_tracker.record_usage("tool1", "capability1", 2.0, True, True, "executor", 0.85)
        self.usage_tracker.record_usage("tool2", "capability1", 50.0, True, False, "executor", 0.60)
        
        report = self.optimizer.get_optimization_report()
        
        self.assertIn("report_generated_at", report)
        self.assertIn("summary", report)
        self.assertIn("performance_analysis", report)
        self.assertIn("recommendations", report)
        self.assertIn("optimization_score", report)
        
        # Check summary statistics
        summary = report["summary"]
        self.assertEqual(summary["total_tools_analyzed"], 2)
        self.assertGreaterEqual(summary["total_recommendations"], 0)
        
        # Check optimization score is between 0 and 1
        self.assertGreaterEqual(report["optimization_score"], 0.0)
        self.assertLessEqual(report["optimization_score"], 1.0)


class TestEnhancedToolManager(unittest.TestCase):
    """Test cases for EnhancedToolManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tool_manager = EnhancedToolManager()
    
    @patch('botted_library.core.enhanced_tools.get_plugin_manager')
    def test_tool_registration(self, mock_get_plugin_manager):
        """Test enhanced tool registration"""
        mock_plugin_manager = Mock()
        mock_registry = Mock()
        mock_plugin_manager.registry = mock_registry
        mock_get_plugin_manager.return_value = mock_plugin_manager
        
        # Mock successful registration
        mock_registry.register_plugin.return_value = True
        mock_plugin_manager.initialize_plugin.return_value = True
        
        self.tool_manager.register_enhanced_tools()
        
        # Verify that register_plugin was called for each tool
        self.assertGreaterEqual(mock_registry.register_plugin.call_count, 3)  # At least core tools
        self.assertGreaterEqual(mock_plugin_manager.initialize_plugin.call_count, 3)
    
    def test_get_tools_for_worker_type(self):
        """Test getting tools for specific worker type"""
        # This test would require actual tool registration, so we'll mock it
        with patch.object(self.tool_manager, 'plugin_manager') as mock_pm:
            mock_registry = Mock()
            mock_pm.registry = mock_registry
            
            # Mock plugin that supports executor
            mock_plugin = Mock(spec=IEnhancedTool)
            mock_plugin.supports_worker_type.return_value = True
            
            mock_registry.list_plugins.return_value = ["test_tool"]
            mock_registry.get_plugin.return_value = mock_plugin
            
            tools = self.tool_manager.get_tools_for_worker_type("executor")
            
            self.assertIn("test_tool", tools)
            mock_plugin.supports_worker_type.assert_called_with("executor")
    
    def test_get_collaborative_tools(self):
        """Test getting collaborative tools"""
        with patch.object(self.tool_manager, 'plugin_manager') as mock_pm:
            mock_registry = Mock()
            mock_pm.registry = mock_registry
            
            # Mock collaborative plugin
            mock_plugin = Mock(spec=IEnhancedTool)
            mock_plugin.supports_collaboration.return_value = True
            
            mock_registry.list_plugins.return_value = ["collab_tool"]
            mock_registry.get_plugin.return_value = mock_plugin
            
            tools = self.tool_manager.get_collaborative_tools()
            
            self.assertIn("collab_tool", tools)
            mock_plugin.supports_collaboration.assert_called_once()


if __name__ == '__main__':
    unittest.main()
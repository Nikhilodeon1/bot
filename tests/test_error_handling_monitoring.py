"""
Comprehensive tests for error handling and monitoring systems.

Tests cover:
- Error recovery system functionality
- Monitoring and performance metrics
- End-to-end collaborative workflows
- Load and stress testing scenarios
"""

import pytest
import threading
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from botted_library.core.error_recovery import (
    ErrorRecoverySystem, FailureType, RecoveryStrategy, FailureRecord, ConnectionHealth
)
from botted_library.core.monitoring_system import (
    MonitoringSystem, MetricType, AlertLevel, PerformanceMetric, Alert, OptimizationRecommendation
)
from botted_library.core.collaborative_server import CollaborativeServer, ServerConfig
from botted_library.core.enhanced_worker_registry import EnhancedWorkerRegistry, WorkerType
from botted_library.core.message_router import MessageRouter
from botted_library.core.exceptions import WorkerError


class TestErrorRecoverySystem:
    """Test suite for the error recovery system."""
    
    @pytest.fixture
    def mock_server(self):
        """Create a mock collaborative server."""
        server = Mock(spec=CollaborativeServer)
        server.server_id = "test-server-123"
        server._worker_registry = Mock(spec=EnhancedWorkerRegistry)
        server._message_router = Mock(spec=MessageRouter)
        return server
    
    @pytest.fixture
    def recovery_system(self, mock_server):
        """Create an error recovery system for testing."""
        config = {
            'max_retry_attempts': 3,
            'retry_delay_base': 0.1,  # Fast retries for testing
            'heartbeat_interval': 1,
            'connection_timeout': 5,
            'task_timeout': 30
        }
        return ErrorRecoverySystem(server_instance=mock_server, config=config)
    
    def test_connection_failure_handling(self, recovery_system):
        """Test handling of connection failures with automatic recovery."""
        component_id = "worker-123"
        error = ConnectionError("Connection refused")
        context = {"host": "localhost", "port": 8765}
        
        # Handle connection failure
        result = recovery_system.handle_connection_failure(component_id, error, context)
        
        assert result is True
        assert component_id in recovery_system.connection_health
        assert not recovery_system.connection_health[component_id].is_healthy
        assert len(recovery_system.failure_records) == 1
        
        # Check failure record
        failure_record = list(recovery_system.failure_records.values())[0]
        assert failure_record.failure_type == FailureType.CONNECTION_FAILURE
        assert failure_record.component == component_id
        assert failure_record.context == context
    
    def test_worker_crash_handling(self, recovery_system):
        """Test handling of worker crashes with task reassignment."""
        worker_id = "worker-456"
        active_tasks = ["task-1", "task-2", "task-3"]
        context = {"crash_reason": "out_of_memory"}
        
        # Mock worker registry for task reassignment
        mock_registry = recovery_system.server_instance._worker_registry
        mock_registry.worker_types = {worker_id: WorkerType.EXECUTOR}
        mock_registry.find_workers_by_type.return_value = [
            {"worker_id": "worker-789", "name": "Backup Worker"}
        ]
        mock_registry.get_load_balanced_worker.return_value = {
            "worker_id": "worker-789", "name": "Backup Worker"
        }
        
        # Handle worker crash
        result = recovery_system.handle_worker_crash(worker_id, active_tasks, context)
        
        assert result is True
        assert worker_id in recovery_system.connection_health
        assert not recovery_system.connection_health[worker_id].is_healthy
        
        # Check that tasks were reassigned
        for task_id in active_tasks:
            assert task_id in recovery_system.task_assignments
            assert recovery_system.task_assignments[task_id] == "worker-789"
    
    def test_resource_conflict_resolution(self, recovery_system):
        """Test resource conflict resolution with priority-based approach."""
        resource_id = "shared-file-1"
        conflicting_workers = ["worker-1", "worker-2", "worker-3"]
        context = {"resource_type": "file", "operation": "write"}
        
        # Mock worker registry with different priorities
        mock_registry = recovery_system.server_instance._worker_registry
        mock_registry.load_balancing_stats = {
            "worker-1": {"priority_score": 5.0},
            "worker-2": {"priority_score": 8.0},  # Highest priority
            "worker-3": {"priority_score": 3.0}
        }
        
        # Handle resource conflict
        result = recovery_system.handle_resource_conflict(resource_id, conflicting_workers, context)
        
        assert result is True
        assert resource_id in recovery_system.resource_locks
        
        # Check that highest priority worker got the lock
        lock_info = recovery_system.resource_locks[resource_id]
        assert lock_info["worker_id"] == "worker-2"
    
    def test_communication_failure_handling(self, recovery_system):
        """Test communication failure handling with message queuing."""
        from_worker = "worker-1"
        to_worker = "worker-2"
        message = {
            "message_type": "task_delegation",
            "content": "Test message",
            "message_id": str(uuid.uuid4())
        }
        error = TimeoutError("Message delivery timeout")
        
        # Handle communication failure
        result = recovery_system.handle_communication_failure(from_worker, to_worker, message, error)
        
        assert result is True
        assert len(recovery_system.message_retry_queue) == 1
        
        # Check retry message
        retry_msg = recovery_system.message_retry_queue[0]
        assert retry_msg["from_worker"] == from_worker
        assert retry_msg["to_worker"] == to_worker
        assert retry_msg["message"] == message
        assert retry_msg["retry_count"] == 0
    
    def test_system_health_monitoring(self, recovery_system):
        """Test system health monitoring and reporting."""
        # Add some test data
        recovery_system._update_connection_health("worker-1", healthy=True)
        recovery_system._update_connection_health("worker-2", healthy=False)
        
        # Create some failure records
        recovery_system._create_failure_record(
            FailureType.CONNECTION_FAILURE,
            "worker-2",
            "Connection lost",
            {}
        )
        
        # Get system health
        health = recovery_system.get_system_health()
        
        assert health["healthy_components"] == 1
        assert health["total_components"] == 2
        assert health["overall_health_percentage"] == 50.0
        assert health["recent_failures"] == 1
        assert health["total_failures"] == 1
    
    def test_connection_recovery_with_exponential_backoff(self, recovery_system):
        """Test connection recovery with exponential backoff."""
        component_id = "worker-test"
        
        # Mock the reconnection attempt to fail initially, then succeed
        call_count = 0
        def mock_reconnection(comp_id):
            nonlocal call_count
            call_count += 1
            return call_count >= 2  # Succeed on second attempt
        
        recovery_system._attempt_reconnection = mock_reconnection
        
        # Create failure record
        failure_record = recovery_system._create_failure_record(
            FailureType.CONNECTION_FAILURE,
            component_id,
            "Test connection failure",
            {}
        )
        
        # Start connection recovery
        recovery_system._start_connection_recovery(component_id, failure_record)
        
        # Wait for recovery to complete
        time.sleep(0.5)
        
        # Check that recovery was attempted multiple times
        assert call_count >= 2
        assert failure_record.is_resolved
    
    def test_cleanup_and_shutdown(self, recovery_system):
        """Test proper cleanup and shutdown of recovery system."""
        # Add some test data
        recovery_system._update_connection_health("worker-1", healthy=True)
        recovery_system.handle_connection_failure("worker-2", Exception("test"), {})
        
        # Shutdown the system
        recovery_system.shutdown()
        
        # Verify cleanup
        assert len(recovery_system.failure_records) == 0
        assert len(recovery_system.connection_health) == 0
        assert len(recovery_system.active_recoveries) == 0


class TestMonitoringSystem:
    """Test suite for the monitoring system."""
    
    @pytest.fixture
    def mock_server(self):
        """Create a mock collaborative server."""
        server = Mock(spec=CollaborativeServer)
        server.get_server_status.return_value = {
            "active_workers": 5,
            "collaborative_spaces": 2
        }
        
        # Mock message router
        mock_router = Mock()
        mock_router.get_routing_statistics.return_value = {
            "total_messages": 100,
            "average_delivery_time_ms": 25.5
        }
        server._message_router = mock_router
        
        # Mock worker registry
        mock_registry = Mock()
        mock_registry.get_registry_statistics.return_value = {
            "performance_metrics": {
                "average_success_rate": 0.95
            }
        }
        server._worker_registry = mock_registry
        
        return server
    
    @pytest.fixture
    def monitoring_system(self, mock_server):
        """Create a monitoring system for testing."""
        config = {
            'collection_interval': 0.1,  # Fast collection for testing
            'retention_hours': 1,
            'enable_system_monitoring': False,  # Disable to avoid psutil issues in tests
            'alert_thresholds': {
                'cpu_usage_percent': {'warning': 80, 'critical': 95},
                'memory_usage_percent': {'warning': 85, 'critical': 95}
            }
        }
        return MonitoringSystem(server_instance=mock_server, config=config)
    
    def test_metric_recording(self, monitoring_system):
        """Test recording and retrieving metrics."""
        # Record some metrics
        monitoring_system.record_metric("test_counter", 5.0, {"component": "test"}, MetricType.COUNTER)
        monitoring_system.record_metric("test_gauge", 75.0, {"unit": "percent"}, MetricType.GAUGE)
        
        # Check metrics were recorded
        assert "test_counter" in monitoring_system.metrics
        assert "test_gauge" in monitoring_system.metrics
        
        counter_metric = monitoring_system.metrics["test_counter"]
        gauge_metric = monitoring_system.metrics["test_gauge"]
        
        assert counter_metric.current_value == 5.0
        assert gauge_metric.current_value == 75.0
        assert len(counter_metric.history) == 1
        assert len(gauge_metric.history) == 1
    
    def test_operation_timing(self, monitoring_system):
        """Test operation timing functionality."""
        # Start timing an operation
        operation_id = monitoring_system.start_operation_timer("test_operation")
        
        # Simulate some work
        time.sleep(0.1)
        
        # Stop timing
        duration = monitoring_system.stop_operation_timer(operation_id, {"worker": "test-worker"})
        
        # Check that duration was recorded
        assert duration >= 0.1
        assert len(monitoring_system.operation_history) == 1
        
        operation_record = monitoring_system.operation_history[0]
        assert operation_record["operation_name"] == "test_operation"
        assert operation_record["duration"] >= 0.1
        assert operation_record["labels"]["worker"] == "test-worker"
    
    def test_worker_metrics(self, monitoring_system):
        """Test worker-specific metric recording."""
        worker_id = "worker-123"
        
        # Record worker metrics
        monitoring_system.record_worker_metric(worker_id, "tasks_completed", 10)
        monitoring_system.record_worker_metric(worker_id, "success_rate", 0.95)
        
        # Check worker metrics were recorded
        assert worker_id in monitoring_system.worker_metrics
        worker_data = monitoring_system.worker_metrics[worker_id]
        
        assert worker_data["tasks_completed"]["value"] == 10
        assert worker_data["success_rate"]["value"] == 0.95
        
        # Check that global metrics were also created
        assert "worker_tasks_completed" in monitoring_system.metrics
        assert "worker_success_rate" in monitoring_system.metrics
    
    def test_alert_creation_and_resolution(self, monitoring_system):
        """Test alert creation and resolution."""
        # Create an alert
        alert_id = monitoring_system.create_alert(
            level=AlertLevel.WARNING,
            title="High CPU Usage",
            description="CPU usage is above 80%",
            component="server",
            metric_name="cpu_usage_percent",
            threshold_value=80.0,
            current_value=85.0
        )
        
        # Check alert was created
        assert alert_id in monitoring_system.alerts
        assert alert_id in monitoring_system.active_alerts
        
        alert = monitoring_system.alerts[alert_id]
        assert alert.level == AlertLevel.WARNING
        assert alert.title == "High CPU Usage"
        assert not alert.is_resolved
        
        # Resolve the alert
        result = monitoring_system.resolve_alert(alert_id)
        
        assert result is True
        assert alert.is_resolved
        assert alert.resolved_at is not None
        assert alert_id not in monitoring_system.active_alerts
    
    def test_optimization_recommendations(self, monitoring_system):
        """Test optimization recommendation system."""
        # Add a recommendation
        rec_id = monitoring_system.add_optimization_recommendation(
            category="performance",
            priority="high",
            title="Optimize Database Queries",
            description="Database queries are taking too long",
            impact="Reduce response time by 30%",
            effort="medium",
            affected_components=["database", "api"],
            metrics_evidence={"avg_query_time": 2.5}
        )
        
        # Check recommendation was added
        assert rec_id in monitoring_system.recommendations
        
        recommendation = monitoring_system.recommendations[rec_id]
        assert recommendation.category == "performance"
        assert recommendation.priority == "high"
        assert not recommendation.implemented
        
        # Get recommendations with filtering
        perf_recs = monitoring_system.get_optimization_recommendations(category="performance")
        assert len(perf_recs) == 1
        assert perf_recs[0].recommendation_id == rec_id
        
        high_priority_recs = monitoring_system.get_optimization_recommendations(priority="high")
        assert len(high_priority_recs) == 1
    
    def test_system_overview(self, monitoring_system):
        """Test system overview generation."""
        # Add some test data
        monitoring_system.record_metric("cpu_usage_percent", 75.0)
        monitoring_system.record_worker_metric("worker-1", "tasks_completed", 5)
        
        # Create an alert
        monitoring_system.create_alert(
            AlertLevel.WARNING, "Test Alert", "Test description", "test"
        )
        
        # Get system overview
        overview = monitoring_system.get_system_overview()
        
        assert "timestamp" in overview
        assert "system_health" in overview
        assert "performance" in overview
        assert "collaboration" in overview
        
        # Check system health
        health = overview["system_health"]
        assert health["status"] == "degraded"  # Due to active alert
        assert health["active_alerts"] == 1
        
        # Check collaboration metrics
        collaboration = overview["collaboration"]
        assert collaboration["active_workers"] == 1  # From worker metrics
    
    def test_performance_report(self, monitoring_system):
        """Test performance report generation."""
        # Add operation history
        for i in range(5):
            op_id = monitoring_system.start_operation_timer("test_op")
            time.sleep(0.01)
            monitoring_system.stop_operation_timer(op_id)
        
        # Add metrics
        monitoring_system.record_metric("response_time", 100.0)
        monitoring_system.record_metric("response_time", 120.0)
        monitoring_system.record_metric("response_time", 90.0)
        
        # Generate report
        report = monitoring_system.get_performance_report(hours=1)
        
        assert "report_period" in report
        assert "operation_analysis" in report
        assert "metric_trends" in report
        
        # Check operation analysis
        op_analysis = report["operation_analysis"]
        assert "test_op" in op_analysis
        
        test_op_stats = op_analysis["test_op"]
        assert test_op_stats["count"] == 5
        assert test_op_stats["average_duration"] > 0
        
        # Check metric trends
        metric_trends = report["metric_trends"]
        assert "response_time" in metric_trends
        
        response_time_trend = metric_trends["response_time"]
        assert response_time_trend["current_value"] == 90.0
        assert response_time_trend["data_points"] == 3
    
    def test_alert_thresholds(self, monitoring_system):
        """Test automatic alert generation based on thresholds."""
        # Record a metric that should trigger an alert
        monitoring_system.record_metric("cpu_usage_percent", 90.0)  # Above warning threshold
        
        # Check that alert was created
        cpu_alerts = [
            alert for alert in monitoring_system.alerts.values()
            if alert.metric_name == "cpu_usage_percent"
        ]
        
        assert len(cpu_alerts) == 1
        alert = cpu_alerts[0]
        assert alert.level == AlertLevel.WARNING
        assert alert.current_value == 90.0
        assert alert.threshold_value == 80.0
    
    def test_metrics_export(self, monitoring_system):
        """Test metrics export functionality."""
        # Add some test metrics
        monitoring_system.record_metric("test_metric_1", 100.0, {"tag": "value1"})
        monitoring_system.record_metric("test_metric_2", 200.0, {"tag": "value2"})
        
        # Export as JSON
        json_export = monitoring_system.export_metrics(format="json", time_range_hours=1)
        
        assert isinstance(json_export, str)
        assert "test_metric_1" in json_export
        assert "test_metric_2" in json_export
        
        # Export as CSV
        csv_export = monitoring_system.export_metrics(format="csv", time_range_hours=1)
        
        assert isinstance(csv_export, str)
        assert "timestamp,metric_name,value,labels" in csv_export
        assert "test_metric_1" in csv_export
    
    def test_alert_subscription(self, monitoring_system):
        """Test alert subscription and notification."""
        alerts_received = []
        
        def alert_callback(alert):
            alerts_received.append(alert)
        
        # Subscribe to alerts
        monitoring_system.subscribe_to_alerts(alert_callback)
        
        # Create an alert
        monitoring_system.create_alert(
            AlertLevel.ERROR, "Test Alert", "Test description", "test"
        )
        
        # Check that callback was called
        assert len(alerts_received) == 1
        assert alerts_received[0].title == "Test Alert"
        
        # Unsubscribe
        result = monitoring_system.unsubscribe_from_alerts(alert_callback)
        assert result is True
        
        # Create another alert
        monitoring_system.create_alert(
            AlertLevel.INFO, "Another Alert", "Another description", "test"
        )
        
        # Should not receive this alert
        assert len(alerts_received) == 1
    
    def test_cleanup_and_shutdown(self, monitoring_system):
        """Test proper cleanup and shutdown of monitoring system."""
        # Add some test data
        monitoring_system.record_metric("test_metric", 50.0)
        monitoring_system.create_alert(AlertLevel.INFO, "Test", "Test", "test")
        
        # Shutdown the system
        monitoring_system.shutdown()
        
        # Verify cleanup
        assert len(monitoring_system.metrics) == 0
        assert len(monitoring_system.alerts) == 0
        assert len(monitoring_system.recommendations) == 0


class TestEndToEndWorkflows:
    """Test end-to-end collaborative workflows with error handling and monitoring."""
    
    @pytest.fixture
    def server_config(self):
        """Create server configuration for testing."""
        return ServerConfig(
            host="localhost",
            port=8766,  # Different port for testing
            max_workers=10,
            message_queue_size=100,
            heartbeat_interval=1,
            auto_cleanup=True,
            log_level="DEBUG"
        )
    
    @pytest.fixture
    def collaborative_server(self, server_config):
        """Create a collaborative server for testing."""
        server = CollaborativeServer(server_config)
        yield server
        # Cleanup
        if server.state.value == "running":
            server.stop_server()
    
    def test_server_startup_with_monitoring(self, collaborative_server):
        """Test server startup with integrated monitoring and error handling."""
        # Start the server
        collaborative_server.start_server()
        
        assert collaborative_server.state.value == "running"
        assert collaborative_server._worker_registry is not None
        assert collaborative_server._message_router is not None
        
        # Check server status
        status = collaborative_server.get_server_status()
        assert status["state"] == "running"
        assert "statistics" in status
        assert "uptime_seconds" in status
        
        # Stop the server
        collaborative_server.stop_server()
        assert collaborative_server.state.value == "stopped"
    
    def test_worker_registration_and_monitoring(self, collaborative_server):
        """Test worker registration with monitoring integration."""
        collaborative_server.start_server()
        
        # Register a worker
        worker_info = {
            "name": "Test Worker",
            "role": "Executor",
            "worker_type": "executor",
            "capabilities": ["task_execution", "data_processing"],
            "enhanced_capabilities": [
                {"name": "task_execution", "level": 8, "description": "Execute tasks efficiently"},
                {"name": "data_processing", "level": 7, "description": "Process data accurately"}
            ]
        }
        
        registration_id = collaborative_server.register_worker("worker-123", worker_info)
        
        assert registration_id is not None
        
        # Check that worker is in registry
        registry = collaborative_server.get_worker_registry()
        active_workers = registry.get_active_workers()
        
        assert len(active_workers) == 1
        assert active_workers[0]["worker_id"] == "worker-123"
        
        # Unregister worker
        collaborative_server.unregister_worker("worker-123")
        
        active_workers = registry.get_active_workers()
        assert len(active_workers) == 0
        
        collaborative_server.stop_server()
    
    def test_message_routing_with_error_handling(self, collaborative_server):
        """Test message routing with error handling and monitoring."""
        collaborative_server.start_server()
        
        # Register two workers
        worker1_info = {
            "name": "Worker 1", "role": "Planner", "worker_type": "planner",
            "capabilities": ["planning"]
        }
        worker2_info = {
            "name": "Worker 2", "role": "Executor", "worker_type": "executor",
            "capabilities": ["execution"]
        }
        
        collaborative_server.register_worker("worker-1", worker1_info)
        collaborative_server.register_worker("worker-2", worker2_info)
        
        # Route a message
        message = {
            "message_type": "task_delegation",
            "content": "Execute this task",
            "priority": "normal"
        }
        
        success = collaborative_server.route_message("worker-1", "worker-2", message)
        assert success is True
        
        # Check routing statistics
        router = collaborative_server._message_router
        stats = router.get_routing_statistics()
        
        assert stats["total_messages"] >= 1
        
        collaborative_server.stop_server()
    
    def test_collaborative_space_creation_and_monitoring(self, collaborative_server):
        """Test collaborative space creation with monitoring."""
        collaborative_server.start_server()
        
        # Register a worker
        worker_info = {"name": "Test Worker", "role": "Planner", "worker_type": "planner"}
        collaborative_server.register_worker("worker-1", worker_info)
        
        # Create a collaborative space
        space = collaborative_server.create_collaborative_space(
            space_name="Test Space",
            created_by="worker-1",
            description="A test collaborative space"
        )
        
        assert space is not None
        assert space.name == "Test Space"
        assert space.created_by == "worker-1"
        
        # List collaborative spaces
        spaces = collaborative_server.list_collaborative_spaces()
        assert len(spaces) == 1
        assert spaces[0].space_id == space.space_id
        
        collaborative_server.stop_server()
    
    @pytest.mark.slow
    def test_load_testing_with_monitoring(self, collaborative_server):
        """Test system behavior under load with monitoring."""
        collaborative_server.start_server()
        
        # Register multiple workers
        for i in range(5):
            worker_info = {
                "name": f"Worker {i}",
                "role": "Executor",
                "worker_type": "executor",
                "capabilities": ["task_execution"]
            }
            collaborative_server.register_worker(f"worker-{i}", worker_info)
        
        # Send multiple messages concurrently
        def send_messages():
            for j in range(10):
                message = {
                    "message_type": "task_delegation",
                    "content": f"Task {j}",
                    "priority": "normal"
                }
                collaborative_server.route_message("worker-0", f"worker-{j % 4 + 1}", message)
        
        # Create multiple threads to simulate load
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=send_messages)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that system handled the load
        router = collaborative_server._message_router
        stats = router.get_routing_statistics()
        
        assert stats["total_messages"] >= 30  # 3 threads * 10 messages each
        
        # Check server status
        status = collaborative_server.get_server_status()
        assert status["state"] == "running"
        assert status["active_workers"] == 5
        
        collaborative_server.stop_server()
    
    def test_error_recovery_integration(self, collaborative_server):
        """Test error recovery integration with the collaborative server."""
        collaborative_server.start_server()
        
        # Register a worker
        worker_info = {"name": "Test Worker", "role": "Executor", "worker_type": "executor"}
        collaborative_server.register_worker("worker-1", worker_info)
        
        # Simulate a connection failure
        try:
            # This should trigger error handling
            collaborative_server.route_message("nonexistent-worker", "worker-1", {"test": "message"})
        except Exception:
            pass  # Expected to fail
        
        # The server should still be running and functional
        status = collaborative_server.get_server_status()
        assert status["state"] == "running"
        
        # Should still be able to route valid messages
        success = collaborative_server.route_message("worker-1", "worker-1", {"test": "self-message"})
        assert success is True
        
        collaborative_server.stop_server()


class TestStressAndPerformance:
    """Stress and performance tests for the error handling and monitoring systems."""
    
    def test_high_frequency_metric_recording(self):
        """Test monitoring system under high-frequency metric recording."""
        monitoring = MonitoringSystem(config={'collection_interval': 0.01})
        
        # Record metrics at high frequency
        start_time = time.time()
        metric_count = 0
        
        while time.time() - start_time < 1.0:  # Run for 1 second
            monitoring.record_metric("high_freq_metric", metric_count)
            metric_count += 1
        
        # Check that system handled high frequency
        metric = monitoring.metrics["high_freq_metric"]
        assert len(metric.history) > 50  # Should have recorded many points
        assert metric.current_value == metric_count - 1
        
        monitoring.shutdown()
    
    def test_concurrent_error_handling(self):
        """Test error recovery system under concurrent failures."""
        recovery = ErrorRecoverySystem(config={'max_retry_attempts': 2, 'retry_delay_base': 0.01})
        
        # Simulate concurrent connection failures
        def simulate_failure(worker_id):
            error = ConnectionError(f"Connection failed for {worker_id}")
            recovery.handle_connection_failure(worker_id, error)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=simulate_failure, args=(f"worker-{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check that all failures were recorded
        assert len(recovery.failure_records) == 10
        assert len(recovery.connection_health) == 10
        
        # All workers should be marked as unhealthy
        for i in range(10):
            worker_id = f"worker-{i}"
            assert worker_id in recovery.connection_health
            assert not recovery.connection_health[worker_id].is_healthy
        
        recovery.shutdown()
    
    def test_memory_usage_under_load(self):
        """Test memory usage of monitoring system under sustained load."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
        except ImportError:
            # Skip test if psutil not available
            pytest.skip("psutil not available for memory testing")
        
        monitoring = MonitoringSystem(config={
            'collection_interval': 0.01,
            'retention_hours': 0.1  # Short retention for testing
        })
        
        # Generate sustained load
        for i in range(1000):
            monitoring.record_metric(f"metric_{i % 10}", i)
            monitoring.start_operation_timer(f"op_{i}")
            
            if i % 100 == 0:
                # Check memory periodically
                current_memory = process.memory_info().rss
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be reasonable (less than 50MB)
                assert memory_growth < 50 * 1024 * 1024, f"Memory growth too high: {memory_growth} bytes"
        
        monitoring.shutdown()
    
    def test_alert_storm_handling(self):
        """Test monitoring system's ability to handle alert storms."""
        monitoring = MonitoringSystem(config={
            'alert_thresholds': {
                'test_metric': {'warning': 50, 'error': 80, 'critical': 95}
            }
        })
        
        # Generate alert storm
        for i in range(100):
            # Alternate between high and low values to trigger multiple alerts
            value = 90 if i % 2 == 0 else 30
            monitoring.record_metric("test_metric", value)
        
        # System should handle the alert storm gracefully
        assert len(monitoring.alerts) > 0
        assert len(monitoring.active_alerts) > 0
        
        # Should not have created excessive alerts (some deduplication should occur)
        assert len(monitoring.alerts) < 50  # Less than half the metric recordings
        
        monitoring.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
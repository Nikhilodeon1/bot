"""
Monitoring and Performance System for Collaborative Server

Provides comprehensive monitoring, performance metrics collection,
logging, and optimization recommendations for distributed operations.
"""

import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import logging
import json

from .exceptions import BottedLibraryError

# Optional psutil import for system monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


class MetricType(Enum):
    """Types of metrics that can be collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Represents a single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetric:
    """Represents a performance metric with history"""
    name: str
    metric_type: MetricType
    description: str
    unit: str
    current_value: float = 0.0
    history: deque = field(default_factory=lambda: deque(maxlen=1000))
    labels: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Alert:
    """Represents a system alert"""
    alert_id: str
    level: AlertLevel
    title: str
    description: str
    component: str
    metric_name: Optional[str] = None
    threshold_value: Optional[float] = None
    current_value: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    is_resolved: bool = False


@dataclass
class OptimizationRecommendation:
    """Represents a system optimization recommendation"""
    recommendation_id: str
    category: str  # performance, resource, configuration
    priority: str  # low, medium, high, critical
    title: str
    description: str
    impact: str  # Expected impact description
    implementation_effort: str  # low, medium, high
    affected_components: List[str]
    metrics_evidence: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    implemented: bool = False


class MonitoringSystem:
    """
    Comprehensive monitoring and performance system.
    
    Features:
    - Real-time performance metrics collection
    - System resource monitoring (CPU, memory, disk, network)
    - Distributed operation monitoring
    - Alert generation and management
    - Performance analysis and optimization recommendations
    - Comprehensive logging system
    """
    
    def __init__(self, server_instance=None, config: Dict[str, Any] = None):
        """
        Initialize the monitoring system.
        
        Args:
            server_instance: Reference to the collaborative server
            config: Configuration parameters for monitoring
        """
        self.server_instance = server_instance
        self.config = config or {}
        
        # Monitoring configuration
        self.collection_interval = self.config.get('collection_interval', 10)  # seconds
        self.retention_hours = self.config.get('retention_hours', 24)
        self.alert_thresholds = self.config.get('alert_thresholds', {})
        self.enable_system_monitoring = self.config.get('enable_system_monitoring', True)
        
        # Metrics storage
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.alerts: Dict[str, Alert] = {}
        self.recommendations: Dict[str, OptimizationRecommendation] = {}
        
        # Performance tracking
        self.operation_timers: Dict[str, float] = {}  # operation_id -> start_time
        self.operation_history: deque = deque(maxlen=10000)
        
        # System resource tracking
        self.system_metrics = {
            'cpu_usage': deque(maxlen=1000),
            'memory_usage': deque(maxlen=1000),
            'disk_usage': deque(maxlen=1000),
            'network_io': deque(maxlen=1000)
        }
        
        # Distributed operation tracking
        self.worker_metrics: Dict[str, Dict[str, Any]] = {}
        self.collaboration_metrics: Dict[str, Any] = {
            'active_collaborations': 0,
            'messages_per_second': 0.0,
            'average_response_time': 0.0,
            'task_completion_rate': 0.0
        }
        
        # Alert management
        self.alert_callbacks: List[Callable] = []
        self.active_alerts: Set[str] = set()
        
        # Threading and lifecycle
        self._monitoring_thread = None
        self._analysis_thread = None
        self._shutdown_event = threading.Event()
        self._lock = threading.RLock()
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.MonitoringSystem")
        
        # Initialize default metrics
        self._initialize_default_metrics()
        
        # Start monitoring threads
        self._start_monitoring_threads()
    
    def record_metric(self, name: str, value: float, labels: Dict[str, str] = None,
                     metric_type: MetricType = MetricType.GAUGE) -> None:
        """
        Record a metric value.
        
        Args:
            name: Name of the metric
            value: Metric value
            labels: Optional labels for the metric
            metric_type: Type of metric (counter, gauge, etc.)
        """
        try:
            with self._lock:
                if name not in self.metrics:
                    self.metrics[name] = PerformanceMetric(
                        name=name,
                        metric_type=metric_type,
                        description=f"Auto-generated metric: {name}",
                        unit="units"
                    )
                
                metric = self.metrics[name]
                
                # Update current value based on metric type
                if metric_type == MetricType.COUNTER:
                    metric.current_value += value
                else:
                    metric.current_value = value
                
                # Add to history
                point = MetricPoint(
                    timestamp=datetime.now(),
                    value=metric.current_value,
                    labels=labels or {}
                )
                metric.history.append(point)
                
                # Check for alerts
                self._check_metric_alerts(name, metric.current_value)
                
        except Exception as e:
            self.logger.error(f"Error recording metric {name}: {e}")
    
    def start_operation_timer(self, operation_name: str, operation_id: str = None) -> str:
        """
        Start timing an operation.
        
        Args:
            operation_name: Name of the operation being timed
            operation_id: Optional custom operation ID
            
        Returns:
            Operation ID for stopping the timer
        """
        if not operation_id:
            operation_id = f"{operation_name}_{uuid.uuid4().hex[:8]}"
        
        with self._lock:
            self.operation_timers[operation_id] = time.time()
        
        return operation_id
    
    def stop_operation_timer(self, operation_id: str, labels: Dict[str, str] = None) -> float:
        """
        Stop timing an operation and record the duration.
        
        Args:
            operation_id: ID of the operation to stop timing
            labels: Optional labels for the timing metric
            
        Returns:
            Duration in seconds
        """
        end_time = time.time()
        
        with self._lock:
            start_time = self.operation_timers.pop(operation_id, None)
        
        if start_time is None:
            self.logger.warning(f"No timer found for operation: {operation_id}")
            return 0.0
        
        duration = end_time - start_time
        
        # Extract operation name from operation_id
        operation_name = operation_id.split('_')[0] if '_' in operation_id else operation_id
        
        # Record timing metric
        self.record_metric(
            f"operation_duration_{operation_name}",
            duration,
            labels,
            MetricType.TIMER
        )
        
        # Add to operation history
        operation_record = {
            'operation_id': operation_id,
            'operation_name': operation_name,
            'duration': duration,
            'timestamp': datetime.now(),
            'labels': labels or {}
        }
        
        with self._lock:
            self.operation_history.append(operation_record)
        
        return duration
    
    def record_worker_metric(self, worker_id: str, metric_name: str, value: float) -> None:
        """
        Record a metric for a specific worker.
        
        Args:
            worker_id: ID of the worker
            metric_name: Name of the metric
            value: Metric value
        """
        with self._lock:
            if worker_id not in self.worker_metrics:
                self.worker_metrics[worker_id] = {}
            
            self.worker_metrics[worker_id][metric_name] = {
                'value': value,
                'timestamp': datetime.now()
            }
        
        # Also record as a global metric with worker label
        self.record_metric(
            f"worker_{metric_name}",
            value,
            {'worker_id': worker_id}
        )
    
    def create_alert(self, level: AlertLevel, title: str, description: str,
                    component: str, metric_name: str = None,
                    threshold_value: float = None, current_value: float = None) -> str:
        """
        Create a new alert.
        
        Args:
            level: Alert severity level
            title: Alert title
            description: Alert description
            component: Component that triggered the alert
            metric_name: Optional metric name that triggered the alert
            threshold_value: Optional threshold value that was exceeded
            current_value: Optional current metric value
            
        Returns:
            Alert ID
        """
        alert_id = str(uuid.uuid4())
        
        alert = Alert(
            alert_id=alert_id,
            level=level,
            title=title,
            description=description,
            component=component,
            metric_name=metric_name,
            threshold_value=threshold_value,
            current_value=current_value
        )
        
        with self._lock:
            self.alerts[alert_id] = alert
            self.active_alerts.add(alert_id)
        
        # Notify alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback error: {e}")
        
        self.logger.warning(f"ALERT [{level.value.upper()}] {title}: {description}")
        
        return alert_id
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an active alert.
        
        Args:
            alert_id: ID of the alert to resolve
            
        Returns:
            True if alert was resolved successfully
        """
        with self._lock:
            if alert_id in self.alerts:
                alert = self.alerts[alert_id]
                alert.is_resolved = True
                alert.resolved_at = datetime.now()
                self.active_alerts.discard(alert_id)
                
                self.logger.info(f"Alert resolved: {alert.title}")
                return True
        
        return False
    
    def add_optimization_recommendation(self, category: str, priority: str, title: str,
                                     description: str, impact: str, effort: str,
                                     affected_components: List[str],
                                     metrics_evidence: Dict[str, Any]) -> str:
        """
        Add an optimization recommendation.
        
        Args:
            category: Recommendation category (performance, resource, configuration)
            priority: Priority level (low, medium, high, critical)
            title: Recommendation title
            description: Detailed description
            impact: Expected impact description
            effort: Implementation effort (low, medium, high)
            affected_components: List of affected components
            metrics_evidence: Supporting metrics data
            
        Returns:
            Recommendation ID
        """
        recommendation_id = str(uuid.uuid4())
        
        recommendation = OptimizationRecommendation(
            recommendation_id=recommendation_id,
            category=category,
            priority=priority,
            title=title,
            description=description,
            impact=impact,
            implementation_effort=effort,
            affected_components=affected_components,
            metrics_evidence=metrics_evidence
        )
        
        with self._lock:
            self.recommendations[recommendation_id] = recommendation
        
        self.logger.info(f"Optimization recommendation added: {title} (Priority: {priority})")
        
        return recommendation_id
    
    def get_system_overview(self) -> Dict[str, Any]:
        """
        Get comprehensive system overview with key metrics.
        
        Returns:
            Dictionary containing system overview data
        """
        with self._lock:
            # Calculate key performance indicators
            total_operations = len(self.operation_history)
            
            if total_operations > 0:
                recent_operations = [
                    op for op in self.operation_history
                    if op['timestamp'] > datetime.now() - timedelta(minutes=5)
                ]
                
                avg_operation_time = sum(op['duration'] for op in recent_operations) / len(recent_operations) if recent_operations else 0.0
                operations_per_minute = len(recent_operations)
            else:
                avg_operation_time = 0.0
                operations_per_minute = 0
            
            # Get current system resources
            system_resources = self._get_current_system_resources()
            
            # Count active components
            active_workers = len(self.worker_metrics)
            active_alerts_count = len(self.active_alerts)
            pending_recommendations = len([
                r for r in self.recommendations.values() if not r.implemented
            ])
            
            return {
                'timestamp': datetime.now().isoformat(),
                'system_health': {
                    'status': 'healthy' if active_alerts_count == 0 else 'degraded',
                    'active_alerts': active_alerts_count,
                    'pending_recommendations': pending_recommendations
                },
                'performance': {
                    'operations_per_minute': operations_per_minute,
                    'average_operation_time_seconds': avg_operation_time,
                    'total_operations': total_operations
                },
                'resources': system_resources,
                'collaboration': {
                    'active_workers': active_workers,
                    **self.collaboration_metrics
                },
                'metrics_summary': {
                    'total_metrics': len(self.metrics),
                    'metrics_with_alerts': len([
                        m for m in self.metrics.values()
                        if any(a.metric_name == m.name for a in self.alerts.values() if not a.is_resolved)
                    ])
                }
            }
    
    def get_performance_report(self, hours: int = 1) -> Dict[str, Any]:
        """
        Generate a detailed performance report.
        
        Args:
            hours: Number of hours to include in the report
            
        Returns:
            Comprehensive performance report
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            # Filter recent operations
            recent_operations = [
                op for op in self.operation_history
                if op['timestamp'] > cutoff_time
            ]
            
            # Analyze operations by type
            operation_stats = defaultdict(list)
            for op in recent_operations:
                operation_stats[op['operation_name']].append(op['duration'])
            
            # Calculate statistics for each operation type
            operation_analysis = {}
            for op_name, durations in operation_stats.items():
                if durations:
                    operation_analysis[op_name] = {
                        'count': len(durations),
                        'average_duration': sum(durations) / len(durations),
                        'min_duration': min(durations),
                        'max_duration': max(durations),
                        'total_time': sum(durations)
                    }
            
            # Get metric trends
            metric_trends = {}
            for name, metric in self.metrics.items():
                recent_points = [
                    point for point in metric.history
                    if point.timestamp > cutoff_time
                ]
                
                if len(recent_points) >= 2:
                    values = [point.value for point in recent_points]
                    metric_trends[name] = {
                        'current_value': metric.current_value,
                        'average_value': sum(values) / len(values),
                        'min_value': min(values),
                        'max_value': max(values),
                        'data_points': len(values),
                        'trend': 'increasing' if values[-1] > values[0] else 'decreasing' if values[-1] < values[0] else 'stable'
                    }
            
            # Get worker performance
            worker_performance = {}
            for worker_id, metrics in self.worker_metrics.items():
                recent_metrics = {
                    name: data for name, data in metrics.items()
                    if data['timestamp'] > cutoff_time
                }
                
                if recent_metrics:
                    worker_performance[worker_id] = recent_metrics
            
            return {
                'report_period': {
                    'start_time': cutoff_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'duration_hours': hours
                },
                'operation_analysis': operation_analysis,
                'metric_trends': metric_trends,
                'worker_performance': worker_performance,
                'system_resources': self._get_resource_trends(hours),
                'alerts_summary': {
                    'total_alerts': len([
                        a for a in self.alerts.values()
                        if a.created_at > cutoff_time
                    ]),
                    'resolved_alerts': len([
                        a for a in self.alerts.values()
                        if a.created_at > cutoff_time and a.is_resolved
                    ]),
                    'active_alerts': len(self.active_alerts)
                }
            }
    
    def get_optimization_recommendations(self, category: str = None,
                                      priority: str = None) -> List[OptimizationRecommendation]:
        """
        Get optimization recommendations with optional filtering.
        
        Args:
            category: Optional category filter
            priority: Optional priority filter
            
        Returns:
            List of matching recommendations
        """
        with self._lock:
            recommendations = list(self.recommendations.values())
        
        # Apply filters
        if category:
            recommendations = [r for r in recommendations if r.category == category]
        
        if priority:
            recommendations = [r for r in recommendations if r.priority == priority]
        
        # Sort by priority and creation time
        priority_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        recommendations.sort(
            key=lambda r: (priority_order.get(r.priority, 0), r.created_at),
            reverse=True
        )
        
        return recommendations
    
    def subscribe_to_alerts(self, callback: Callable[[Alert], None]) -> None:
        """
        Subscribe to alert notifications.
        
        Args:
            callback: Function to call when alerts are created
        """
        self.alert_callbacks.append(callback)
    
    def unsubscribe_from_alerts(self, callback: Callable[[Alert], None]) -> bool:
        """
        Unsubscribe from alert notifications.
        
        Args:
            callback: Callback function to remove
            
        Returns:
            True if unsubscribed successfully
        """
        try:
            self.alert_callbacks.remove(callback)
            return True
        except ValueError:
            return False
    
    def export_metrics(self, format: str = 'json', time_range_hours: int = 1) -> str:
        """
        Export metrics data in specified format.
        
        Args:
            format: Export format ('json', 'csv')
            time_range_hours: Hours of data to export
            
        Returns:
            Exported data as string
        """
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'time_range_hours': time_range_hours,
            'metrics': {}
        }
        
        with self._lock:
            for name, metric in self.metrics.items():
                recent_points = [
                    {
                        'timestamp': point.timestamp.isoformat(),
                        'value': point.value,
                        'labels': point.labels
                    }
                    for point in metric.history
                    if point.timestamp > cutoff_time
                ]
                
                export_data['metrics'][name] = {
                    'type': metric.metric_type.value,
                    'description': metric.description,
                    'unit': metric.unit,
                    'current_value': metric.current_value,
                    'data_points': recent_points
                }
        
        if format.lower() == 'json':
            return json.dumps(export_data, indent=2)
        elif format.lower() == 'csv':
            # Simple CSV export (would need more sophisticated implementation for production)
            lines = ['timestamp,metric_name,value,labels']
            for name, metric_data in export_data['metrics'].items():
                for point in metric_data['data_points']:
                    labels_str = json.dumps(point['labels'])
                    lines.append(f"{point['timestamp']},{name},{point['value']},{labels_str}")
            return '\n'.join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def shutdown(self) -> None:
        """Shutdown the monitoring system."""
        self.logger.info("Shutting down monitoring system...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for threads to complete
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        
        if self._analysis_thread and self._analysis_thread.is_alive():
            self._analysis_thread.join(timeout=5)
        
        # Clear data structures
        with self._lock:
            self.metrics.clear()
            self.alerts.clear()
            self.recommendations.clear()
            self.worker_metrics.clear()
            self.operation_timers.clear()
        
        self.logger.info("Monitoring system shutdown complete")
    
    def _initialize_default_metrics(self) -> None:
        """Initialize default system metrics."""
        default_metrics = [
            ('cpu_usage_percent', MetricType.GAUGE, 'CPU usage percentage', '%'),
            ('memory_usage_percent', MetricType.GAUGE, 'Memory usage percentage', '%'),
            ('disk_usage_percent', MetricType.GAUGE, 'Disk usage percentage', '%'),
            ('active_workers', MetricType.GAUGE, 'Number of active workers', 'count'),
            ('messages_per_second', MetricType.GAUGE, 'Messages processed per second', 'msg/s'),
            ('average_response_time', MetricType.GAUGE, 'Average response time', 'ms'),
            ('error_rate', MetricType.GAUGE, 'Error rate percentage', '%'),
            ('task_completion_rate', MetricType.GAUGE, 'Task completion rate', 'tasks/min')
        ]
        
        for name, metric_type, description, unit in default_metrics:
            self.metrics[name] = PerformanceMetric(
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit
            )
    
    def _start_monitoring_threads(self) -> None:
        """Start background monitoring threads."""
        # Main monitoring thread
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="SystemMonitoring"
        )
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()
        
        # Analysis and recommendation thread
        self._analysis_thread = threading.Thread(
            target=self._analysis_loop,
            name="PerformanceAnalysis"
        )
        self._analysis_thread.daemon = True
        self._analysis_thread.start()
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop for collecting system metrics."""
        self.logger.debug("Monitoring loop started")
        
        try:
            while not self._shutdown_event.is_set():
                # Collect system metrics
                if self.enable_system_monitoring:
                    self._collect_system_metrics()
                
                # Collect collaboration metrics
                self._collect_collaboration_metrics()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Wait for next collection interval
                if self._shutdown_event.wait(timeout=self.collection_interval):
                    break
                    
        except Exception as e:
            self.logger.error(f"Monitoring loop error: {e}")
        
        self.logger.debug("Monitoring loop completed")
    
    def _analysis_loop(self) -> None:
        """Analysis loop for generating recommendations and detecting issues."""
        self.logger.debug("Analysis loop started")
        
        try:
            while not self._shutdown_event.is_set():
                # Analyze performance trends
                self._analyze_performance_trends()
                
                # Generate optimization recommendations
                self._generate_optimization_recommendations()
                
                # Check for anomalies
                self._detect_anomalies()
                
                # Wait before next analysis (longer interval)
                if self._shutdown_event.wait(timeout=60):  # Analyze every minute
                    break
                    
        except Exception as e:
            self.logger.error(f"Analysis loop error: {e}")
        
        self.logger.debug("Analysis loop completed")
    
    def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        if not PSUTIL_AVAILABLE:
            # Use mock values for testing when psutil is not available
            cpu_percent = 25.0
            memory_percent = 45.0
            disk_percent = 60.0
            bytes_sent = 1000
            bytes_recv = 2000
        else:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                
                # Network I/O
                network = psutil.net_io_counters()
                bytes_sent = network.bytes_sent
                bytes_recv = network.bytes_recv
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
                return
        
        try:
            # Record metrics
            self.record_metric('cpu_usage_percent', cpu_percent)
            self.record_metric('memory_usage_percent', memory_percent)
            self.record_metric('disk_usage_percent', disk_percent)
            self.record_metric('network_bytes_sent', bytes_sent, metric_type=MetricType.COUNTER)
            self.record_metric('network_bytes_recv', bytes_recv, metric_type=MetricType.COUNTER)
            
            # Store in system metrics for trending
            now = datetime.now()
            with self._lock:
                self.system_metrics['cpu_usage'].append((now, cpu_percent))
                self.system_metrics['memory_usage'].append((now, memory_percent))
                self.system_metrics['disk_usage'].append((now, disk_percent))
                self.system_metrics['network_io'].append((now, bytes_sent + bytes_recv))
            
        except Exception as e:
            self.logger.error(f"Error recording system metrics: {e}")
    
    def _collect_collaboration_metrics(self) -> None:
        """Collect collaboration-specific metrics."""
        try:
            if not self.server_instance:
                return
            
            # Get server status
            server_status = self.server_instance.get_server_status()
            
            # Record active workers
            active_workers = server_status.get('active_workers', 0)
            self.record_metric('active_workers', active_workers)
            
            # Get message router statistics if available
            if hasattr(self.server_instance, '_message_router') and self.server_instance._message_router:
                router_stats = self.server_instance._message_router.get_routing_statistics()
                
                # Calculate messages per second
                total_messages = router_stats.get('total_messages', 0)
                if hasattr(self, '_last_message_count'):
                    messages_delta = total_messages - self._last_message_count
                    messages_per_second = messages_delta / self.collection_interval
                    self.record_metric('messages_per_second', messages_per_second)
                
                self._last_message_count = total_messages
                
                # Record average delivery time
                avg_delivery_time = router_stats.get('average_delivery_time_ms', 0.0)
                self.record_metric('average_response_time', avg_delivery_time)
            
            # Get worker registry statistics if available
            if hasattr(self.server_instance, '_worker_registry') and self.server_instance._worker_registry:
                registry_stats = self.server_instance._worker_registry.get_registry_statistics()
                
                # Record performance metrics
                perf_metrics = registry_stats.get('performance_metrics', {})
                success_rate = perf_metrics.get('average_success_rate', 1.0) * 100
                self.record_metric('task_success_rate', success_rate)
                
                # Calculate error rate
                error_rate = (1.0 - perf_metrics.get('average_success_rate', 1.0)) * 100
                self.record_metric('error_rate', error_rate)
            
        except Exception as e:
            self.logger.error(f"Error collecting collaboration metrics: {e}")
    
    def _check_metric_alerts(self, metric_name: str, value: float) -> None:
        """Check if a metric value triggers any alerts."""
        thresholds = self.alert_thresholds.get(metric_name, {})
        
        for level_str, threshold in thresholds.items():
            try:
                level = AlertLevel(level_str.lower())
                
                # Check if threshold is exceeded
                if value > threshold:
                    # Check if we already have an active alert for this
                    existing_alert = None
                    for alert in self.alerts.values():
                        if (alert.metric_name == metric_name and 
                            alert.level == level and 
                            not alert.is_resolved):
                            existing_alert = alert
                            break
                    
                    if not existing_alert:
                        self.create_alert(
                            level=level,
                            title=f"{metric_name} threshold exceeded",
                            description=f"{metric_name} value {value} exceeds {level_str} threshold {threshold}",
                            component="system",
                            metric_name=metric_name,
                            threshold_value=threshold,
                            current_value=value
                        )
                        
            except ValueError:
                # Invalid alert level
                continue
    
    def _analyze_performance_trends(self) -> None:
        """Analyze performance trends and identify issues."""
        try:
            # Analyze recent operation performance
            recent_operations = [
                op for op in self.operation_history
                if op['timestamp'] > datetime.now() - timedelta(minutes=10)
            ]
            
            if len(recent_operations) > 10:
                # Group by operation type
                operation_groups = defaultdict(list)
                for op in recent_operations:
                    operation_groups[op['operation_name']].append(op['duration'])
                
                # Check for performance degradation
                for op_name, durations in operation_groups.items():
                    if len(durations) >= 5:
                        avg_duration = sum(durations) / len(durations)
                        max_duration = max(durations)
                        
                        # Check if operations are taking too long
                        if avg_duration > 5.0:  # 5 seconds threshold
                            self.create_alert(
                                level=AlertLevel.WARNING,
                                title=f"Slow operation detected: {op_name}",
                                description=f"Average duration: {avg_duration:.2f}s, Max: {max_duration:.2f}s",
                                component=op_name,
                                metric_name=f"operation_duration_{op_name}",
                                current_value=avg_duration
                            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance trends: {e}")
    
    def _generate_optimization_recommendations(self) -> None:
        """Generate optimization recommendations based on current metrics."""
        try:
            # Check CPU usage
            cpu_metric = self.metrics.get('cpu_usage_percent')
            if cpu_metric and cpu_metric.current_value > 80:
                # Check if we already have this recommendation
                existing = any(
                    r.category == 'performance' and 'CPU' in r.title and not r.implemented
                    for r in self.recommendations.values()
                )
                
                if not existing:
                    self.add_optimization_recommendation(
                        category='performance',
                        priority='high',
                        title='High CPU Usage Detected',
                        description='System CPU usage is consistently above 80%. Consider optimizing worker algorithms or scaling horizontally.',
                        impact='Reduced response times and improved system stability',
                        effort='medium',
                        affected_components=['server', 'workers'],
                        metrics_evidence={'cpu_usage_percent': cpu_metric.current_value}
                    )
            
            # Check memory usage
            memory_metric = self.metrics.get('memory_usage_percent')
            if memory_metric and memory_metric.current_value > 85:
                existing = any(
                    r.category == 'resource' and 'memory' in r.title.lower() and not r.implemented
                    for r in self.recommendations.values()
                )
                
                if not existing:
                    self.add_optimization_recommendation(
                        category='resource',
                        priority='high',
                        title='High Memory Usage Detected',
                        description='System memory usage is above 85%. Consider implementing memory cleanup or increasing available memory.',
                        impact='Prevent out-of-memory errors and improve performance',
                        effort='low',
                        affected_components=['server'],
                        metrics_evidence={'memory_usage_percent': memory_metric.current_value}
                    )
            
            # Check error rate
            error_rate_metric = self.metrics.get('error_rate')
            if error_rate_metric and error_rate_metric.current_value > 5:
                existing = any(
                    r.category == 'performance' and 'error' in r.title.lower() and not r.implemented
                    for r in self.recommendations.values()
                )
                
                if not existing:
                    self.add_optimization_recommendation(
                        category='performance',
                        priority='critical',
                        title='High Error Rate Detected',
                        description=f'System error rate is {error_rate_metric.current_value:.1f}%. Investigate and fix underlying issues.',
                        impact='Improved system reliability and user experience',
                        effort='high',
                        affected_components=['server', 'workers', 'communication'],
                        metrics_evidence={'error_rate': error_rate_metric.current_value}
                    )
            
        except Exception as e:
            self.logger.error(f"Error generating optimization recommendations: {e}")
    
    def _detect_anomalies(self) -> None:
        """Detect anomalies in system behavior."""
        try:
            # Check for sudden spikes in metrics
            for name, metric in self.metrics.items():
                if len(metric.history) >= 10:
                    recent_values = [point.value for point in list(metric.history)[-10:]]
                    avg_value = sum(recent_values) / len(recent_values)
                    current_value = metric.current_value
                    
                    # Check for sudden spike (current value > 2x average)
                    if current_value > avg_value * 2 and avg_value > 0:
                        self.create_alert(
                            level=AlertLevel.WARNING,
                            title=f"Anomaly detected in {name}",
                            description=f"Current value {current_value:.2f} is significantly higher than recent average {avg_value:.2f}",
                            component="system",
                            metric_name=name,
                            current_value=current_value
                        )
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
    
    def _cleanup_old_data(self) -> None:
        """Clean up old metric data to prevent memory growth."""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        with self._lock:
            # Clean up metric history
            for metric in self.metrics.values():
                # Remove old points (deque automatically limits size, but we can be more aggressive)
                while metric.history and metric.history[0].timestamp < cutoff_time:
                    metric.history.popleft()
            
            # Clean up operation history
            while self.operation_history and self.operation_history[0]['timestamp'] < cutoff_time:
                self.operation_history.popleft()
            
            # Clean up system metrics
            for metric_name, data in self.system_metrics.items():
                while data and data[0][0] < cutoff_time:
                    data.popleft()
    
    def _get_current_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage."""
        if not PSUTIL_AVAILABLE:
            return {
                'cpu_percent': 25.0,
                'memory_percent': 45.0,
                'disk_percent': 60.0,
                'load_average': [0.5, 0.3, 0.2]
            }
        
        try:
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            }
        except Exception as e:
            self.logger.error(f"Error getting system resources: {e}")
            return {}
    
    def _get_resource_trends(self, hours: int) -> Dict[str, Any]:
        """Get resource usage trends over specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        trends = {}
        
        with self._lock:
            for resource_name, data in self.system_metrics.items():
                recent_data = [(timestamp, value) for timestamp, value in data if timestamp > cutoff_time]
                
                if recent_data:
                    values = [value for _, value in recent_data]
                    trends[resource_name] = {
                        'current': values[-1] if values else 0,
                        'average': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'trend': 'increasing' if len(values) > 1 and values[-1] > values[0] else 'decreasing' if len(values) > 1 and values[-1] < values[0] else 'stable'
                    }
        
        return trends
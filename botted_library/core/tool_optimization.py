"""
Tool Usage Optimization System

Provides optimization capabilities for tool usage tracking, performance analysis,
and collaborative tool usage patterns.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass

from .exceptions import WorkerError


@dataclass
class ToolUsageMetrics:
    """Metrics for tool usage analysis"""
    tool_name: str
    capability_name: str
    usage_count: int
    total_execution_time: float
    average_execution_time: float
    success_rate: float
    collaborative_usage_count: int
    worker_types_used: List[str]
    performance_score: float
    last_used: datetime


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation for tool usage"""
    tool_name: str
    recommendation_type: str
    description: str
    expected_improvement: float
    implementation_priority: str
    collaborative_impact: bool


class ToolUsageTracker:
    """Tracks tool usage patterns and performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._usage_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_uses': 0,
            'capabilities_used': defaultdict(int),
            'execution_times': [],
            'success_count': 0,
            'failure_count': 0,
            'collaborative_uses': 0,
            'worker_types': Counter(),
            'first_used': None,
            'last_used': None,
            'performance_scores': []
        })
        
    def record_usage(self, tool_name: str, capability_name: str, execution_time: float,
                    success: bool, collaborative: bool = False, worker_type: str = None,
                    performance_score: float = None) -> None:
        """Record tool usage event"""
        try:
            data = self._usage_data[tool_name]
            current_time = datetime.now()
            
            # Update basic metrics
            data['total_uses'] += 1
            data['capabilities_used'][capability_name] += 1
            data['execution_times'].append(execution_time)
            
            if success:
                data['success_count'] += 1
            else:
                data['failure_count'] += 1
            
            if collaborative:
                data['collaborative_uses'] += 1
            
            if worker_type:
                data['worker_types'][worker_type] += 1
            
            if performance_score is not None:
                data['performance_scores'].append(performance_score)
            
            # Update timestamps
            if data['first_used'] is None:
                data['first_used'] = current_time
            data['last_used'] = current_time
            
            self.logger.debug(f"Recorded usage for {tool_name}.{capability_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to record tool usage: {str(e)}")
    
    def get_tool_metrics(self, tool_name: str) -> Optional[ToolUsageMetrics]:
        """Get comprehensive metrics for a specific tool"""
        if tool_name not in self._usage_data:
            return None
        
        data = self._usage_data[tool_name]
        
        # Calculate metrics
        total_uses = data['total_uses']
        if total_uses == 0:
            return None
        
        avg_execution_time = sum(data['execution_times']) / len(data['execution_times']) if data['execution_times'] else 0
        success_rate = data['success_count'] / total_uses if total_uses > 0 else 0
        avg_performance_score = sum(data['performance_scores']) / len(data['performance_scores']) if data['performance_scores'] else 0.5
        
        # Get most used capability
        most_used_capability = max(data['capabilities_used'].items(), key=lambda x: x[1])[0] if data['capabilities_used'] else 'unknown'
        
        return ToolUsageMetrics(
            tool_name=tool_name,
            capability_name=most_used_capability,
            usage_count=total_uses,
            total_execution_time=sum(data['execution_times']),
            average_execution_time=avg_execution_time,
            success_rate=success_rate,
            collaborative_usage_count=data['collaborative_uses'],
            worker_types_used=list(data['worker_types'].keys()),
            performance_score=avg_performance_score,
            last_used=data['last_used']
        )
    
    def get_all_metrics(self) -> List[ToolUsageMetrics]:
        """Get metrics for all tracked tools"""
        metrics = []
        for tool_name in self._usage_data.keys():
            tool_metrics = self.get_tool_metrics(tool_name)
            if tool_metrics:
                metrics.append(tool_metrics)
        return metrics
    
    def get_usage_patterns(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Analyze usage patterns within a time window"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        
        patterns = {
            'most_used_tools': [],
            'collaborative_usage_ratio': 0.0,
            'worker_type_distribution': Counter(),
            'peak_usage_hours': Counter(),
            'capability_popularity': Counter(),
            'performance_trends': {}
        }
        
        total_uses = 0
        collaborative_uses = 0
        
        for tool_name, data in self._usage_data.items():
            if data['last_used'] and data['last_used'] >= cutoff_time:
                total_uses += data['total_uses']
                collaborative_uses += data['collaborative_uses']
                
                patterns['most_used_tools'].append((tool_name, data['total_uses']))
                patterns['worker_type_distribution'].update(data['worker_types'])
                patterns['capability_popularity'].update(data['capabilities_used'])
                
                # Calculate performance trend
                if data['performance_scores']:
                    patterns['performance_trends'][tool_name] = {
                        'average_score': sum(data['performance_scores']) / len(data['performance_scores']),
                        'trend': 'stable'  # Simplified - would calculate actual trend
                    }
        
        # Sort and limit results
        patterns['most_used_tools'] = sorted(patterns['most_used_tools'], key=lambda x: x[1], reverse=True)[:10]
        patterns['collaborative_usage_ratio'] = collaborative_uses / total_uses if total_uses > 0 else 0
        
        return patterns
    
    def clear_old_data(self, days_to_keep: int = 30) -> None:
        """Clear usage data older than specified days"""
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        
        tools_to_remove = []
        for tool_name, data in self._usage_data.items():
            if data['last_used'] and data['last_used'] < cutoff_time:
                tools_to_remove.append(tool_name)
        
        for tool_name in tools_to_remove:
            del self._usage_data[tool_name]
            self.logger.info(f"Cleared old usage data for tool: {tool_name}")


class ToolOptimizer:
    """Analyzes tool usage and provides optimization recommendations"""
    
    def __init__(self, usage_tracker: ToolUsageTracker):
        self.logger = logging.getLogger(__name__)
        self.usage_tracker = usage_tracker
        
    def analyze_performance(self, tool_name: str = None) -> Dict[str, Any]:
        """Analyze tool performance and identify optimization opportunities"""
        if tool_name:
            metrics = [self.usage_tracker.get_tool_metrics(tool_name)]
            metrics = [m for m in metrics if m is not None]
        else:
            metrics = self.usage_tracker.get_all_metrics()
        
        analysis = {
            'performance_summary': {},
            'bottlenecks': [],
            'underutilized_tools': [],
            'high_performing_tools': [],
            'collaborative_opportunities': []
        }
        
        for metric in metrics:
            # Performance classification
            if metric.performance_score > 0.8 and metric.success_rate > 0.9:
                analysis['high_performing_tools'].append(metric.tool_name)
            elif metric.average_execution_time > 60 or metric.success_rate < 0.7:
                analysis['bottlenecks'].append({
                    'tool_name': metric.tool_name,
                    'issue': 'slow_execution' if metric.average_execution_time > 60 else 'low_success_rate',
                    'metric_value': metric.average_execution_time if metric.average_execution_time > 60 else metric.success_rate
                })
            
            # Underutilization check
            if metric.usage_count < 10 and (datetime.now() - metric.last_used).days > 7:
                analysis['underutilized_tools'].append(metric.tool_name)
            
            # Collaborative opportunities
            collaborative_ratio = metric.collaborative_usage_count / metric.usage_count if metric.usage_count > 0 else 0
            if collaborative_ratio < 0.3 and len(metric.worker_types_used) > 1:
                analysis['collaborative_opportunities'].append({
                    'tool_name': metric.tool_name,
                    'current_ratio': collaborative_ratio,
                    'potential_improvement': 'increase_collaborative_usage'
                })
            
            # Performance summary
            analysis['performance_summary'][metric.tool_name] = {
                'usage_count': metric.usage_count,
                'success_rate': metric.success_rate,
                'performance_score': metric.performance_score,
                'collaborative_ratio': collaborative_ratio
            }
        
        return analysis
    
    def generate_recommendations(self, analysis: Dict[str, Any] = None) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on analysis"""
        if analysis is None:
            analysis = self.analyze_performance()
        
        recommendations = []
        
        # Recommendations for bottlenecks
        for bottleneck in analysis['bottlenecks']:
            if bottleneck['issue'] == 'slow_execution':
                recommendations.append(OptimizationRecommendation(
                    tool_name=bottleneck['tool_name'],
                    recommendation_type='performance',
                    description=f"Optimize execution time (currently {bottleneck['metric_value']:.1f}s average)",
                    expected_improvement=0.3,
                    implementation_priority='high',
                    collaborative_impact=False
                ))
            elif bottleneck['issue'] == 'low_success_rate':
                recommendations.append(OptimizationRecommendation(
                    tool_name=bottleneck['tool_name'],
                    recommendation_type='reliability',
                    description=f"Improve success rate (currently {bottleneck['metric_value']:.1%})",
                    expected_improvement=0.2,
                    implementation_priority='high',
                    collaborative_impact=False
                ))
        
        # Recommendations for underutilized tools
        for tool_name in analysis['underutilized_tools']:
            recommendations.append(OptimizationRecommendation(
                tool_name=tool_name,
                recommendation_type='utilization',
                description="Increase tool usage through better discovery and documentation",
                expected_improvement=0.5,
                implementation_priority='medium',
                collaborative_impact=False
            ))
        
        # Recommendations for collaborative opportunities
        for opportunity in analysis['collaborative_opportunities']:
            recommendations.append(OptimizationRecommendation(
                tool_name=opportunity['tool_name'],
                recommendation_type='collaboration',
                description=f"Increase collaborative usage (currently {opportunity['current_ratio']:.1%})",
                expected_improvement=0.4,
                implementation_priority='medium',
                collaborative_impact=True
            ))
        
        # General recommendations for high-performing tools
        for tool_name in analysis['high_performing_tools']:
            recommendations.append(OptimizationRecommendation(
                tool_name=tool_name,
                recommendation_type='scaling',
                description="Consider expanding capabilities or promoting wider usage",
                expected_improvement=0.2,
                implementation_priority='low',
                collaborative_impact=True
            ))
        
        return recommendations
    
    def optimize_tool_selection(self, required_capabilities: List[str], 
                              worker_type: str = None, collaborative: bool = False) -> List[Tuple[str, float]]:
        """Recommend optimal tools for given requirements"""
        all_metrics = self.usage_tracker.get_all_metrics()
        
        # Score tools based on requirements
        tool_scores = []
        
        for metric in all_metrics:
            score = 0.0
            
            # Base score from performance and reliability
            score += metric.performance_score * 0.4
            score += metric.success_rate * 0.3
            
            # Bonus for recent usage
            days_since_use = (datetime.now() - metric.last_used).days if metric.last_used else 999
            recency_bonus = max(0, (30 - days_since_use) / 30) * 0.1
            score += recency_bonus
            
            # Bonus for worker type compatibility
            if worker_type and worker_type in metric.worker_types_used:
                score += 0.1
            
            # Bonus for collaborative usage if required
            if collaborative:
                collaborative_ratio = metric.collaborative_usage_count / metric.usage_count if metric.usage_count > 0 else 0
                score += collaborative_ratio * 0.1
            
            # Penalty for low usage (might indicate issues)
            if metric.usage_count < 5:
                score -= 0.1
            
            tool_scores.append((metric.tool_name, score))
        
        # Sort by score and return top recommendations
        tool_scores.sort(key=lambda x: x[1], reverse=True)
        return tool_scores[:5]  # Top 5 recommendations
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        analysis = self.analyze_performance()
        recommendations = self.generate_recommendations(analysis)
        usage_patterns = self.usage_tracker.get_usage_patterns()
        
        report = {
            'report_generated_at': datetime.now().isoformat(),
            'summary': {
                'total_tools_analyzed': len(analysis['performance_summary']),
                'high_performing_tools': len(analysis['high_performing_tools']),
                'bottlenecks_identified': len(analysis['bottlenecks']),
                'underutilized_tools': len(analysis['underutilized_tools']),
                'collaborative_opportunities': len(analysis['collaborative_opportunities']),
                'total_recommendations': len(recommendations)
            },
            'performance_analysis': analysis,
            'usage_patterns': usage_patterns,
            'recommendations': [
                {
                    'tool_name': rec.tool_name,
                    'type': rec.recommendation_type,
                    'description': rec.description,
                    'expected_improvement': rec.expected_improvement,
                    'priority': rec.implementation_priority,
                    'collaborative_impact': rec.collaborative_impact
                }
                for rec in recommendations
            ],
            'optimization_score': self._calculate_optimization_score(analysis),
            'next_review_date': (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        return report
    
    def _calculate_optimization_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall optimization score (0-1)"""
        total_tools = len(analysis['performance_summary'])
        if total_tools == 0:
            return 0.0
        
        # Base score from performance
        performance_scores = [
            summary['performance_score'] 
            for summary in analysis['performance_summary'].values()
        ]
        avg_performance = sum(performance_scores) / len(performance_scores) if performance_scores else 0
        
        # Penalties for issues
        bottleneck_penalty = len(analysis['bottlenecks']) / total_tools * 0.2
        underutilization_penalty = len(analysis['underutilized_tools']) / total_tools * 0.1
        
        # Bonus for collaborative usage
        collaborative_scores = [
            summary.get('collaborative_ratio', 0) 
            for summary in analysis['performance_summary'].values()
        ]
        avg_collaborative = sum(collaborative_scores) / len(collaborative_scores) if collaborative_scores else 0
        collaborative_bonus = avg_collaborative * 0.1
        
        optimization_score = avg_performance - bottleneck_penalty - underutilization_penalty + collaborative_bonus
        return max(0.0, min(1.0, optimization_score))


# Global instances
_tool_usage_tracker = None
_tool_optimizer = None


def get_tool_usage_tracker() -> ToolUsageTracker:
    """Get the global tool usage tracker instance"""
    global _tool_usage_tracker
    if _tool_usage_tracker is None:
        _tool_usage_tracker = ToolUsageTracker()
    return _tool_usage_tracker


def get_tool_optimizer() -> ToolOptimizer:
    """Get the global tool optimizer instance"""
    global _tool_optimizer
    if _tool_optimizer is None:
        _tool_optimizer = ToolOptimizer(get_tool_usage_tracker())
    return _tool_optimizer
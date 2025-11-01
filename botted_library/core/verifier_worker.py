"""
Verifier Worker Implementation

Specialized worker type that validates output quality, provides feedback,
and ensures standards compliance in the collaborative system.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .enhanced_worker import EnhancedWorker
from .enhanced_worker_registry import WorkerType
from .message_router import MessageType
from .exceptions import WorkerError


class VerificationStatus(Enum):
    """Status of verification process"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class QualityLevel(Enum):
    """Quality assessment levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


@dataclass
class VerificationResult:
    """Result of output verification"""
    verification_id: str
    output_verified: Any
    status: VerificationStatus
    quality_level: QualityLevel
    quality_score: float  # 0.0 to 1.0
    feedback: List[str]
    improvement_suggestions: List[str]
    verification_criteria: Dict[str, Any]
    verified_by: str
    verified_at: datetime
    details: Optional[Dict[str, Any]] = None


@dataclass
class QualityMetrics:
    """Quality metrics tracking"""
    total_verifications: int
    approved_count: int
    rejected_count: int
    average_quality_score: float
    quality_distribution: Dict[QualityLevel, int]
    common_issues: List[Dict[str, Any]]
    improvement_trends: Dict[str, float]
    last_updated: datetime


@dataclass
class FeedbackItem:
    """Individual feedback item"""
    feedback_id: str
    category: str  # e.g., "accuracy", "completeness", "format"
    severity: str  # "low", "medium", "high", "critical"
    message: str
    suggestion: Optional[str] = None
    location: Optional[str] = None  # Where in the output the issue occurs


class VerifierWorker(EnhancedWorker):
    """
    Verifier worker specialization for quality validation and feedback.
    
    Capabilities:
    - Validate output quality against criteria
    - Provide detailed feedback and improvement suggestions
    - Track quality metrics and trends
    - Enforce quality standards
    - Generate quality reports
    """
    
    def __init__(self, name: str, role: str, memory_system, knowledge_validator,
                 browser_controller, task_executor, server_connection=None,
                 worker_id=None, config=None):
        """
        Initialize verifier worker.
        
        Args:
            name: Human-readable name for the verifier
            role: Verifier's role/title
            memory_system: Memory system instance
            knowledge_validator: Knowledge validator instance
            browser_controller: Browser controller instance
            task_executor: Task executor instance
            server_connection: Connection to collaborative server
            worker_id: Optional unique identifier
            config: Optional configuration parameters
        """
        super().__init__(
            name=name,
            role=role,
            worker_type=WorkerType.VERIFIER,
            memory_system=memory_system,
            knowledge_validator=knowledge_validator,
            browser_controller=browser_controller,
            task_executor=task_executor,
            server_connection=server_connection,
            worker_id=worker_id,
            config=config or {}
        )
        
        # Verifier-specific state
        self.active_verifications: Dict[str, Dict[str, Any]] = {}
        self.completed_verifications: Dict[str, VerificationResult] = {}
        self.quality_metrics = QualityMetrics(
            total_verifications=0,
            approved_count=0,
            rejected_count=0,
            average_quality_score=0.0,
            quality_distribution={level: 0 for level in QualityLevel},
            common_issues=[],
            improvement_trends={},
            last_updated=datetime.now()
        )
        
        # Verification capabilities
        self.quality_threshold = config.get('quality_threshold', 0.7)
        self.strict_mode = config.get('strict_mode', False)
        self.auto_feedback = config.get('auto_feedback', True)
        self.max_concurrent_verifications = config.get('max_concurrent_verifications', 5)
        
        # Quality standards and criteria
        self.default_criteria = config.get('default_criteria', {
            'accuracy': 0.8,
            'completeness': 0.7,
            'clarity': 0.6,
            'format': 0.5
        })
        
        # Override message handlers for verifier-specific behavior
        self._setup_verifier_message_handlers()
        
        self.logger.info(f"VerifierWorker {name} initialized")
    
    def validate_output_quality(self, output_to_verify: Any, 
                              verification_criteria: Optional[Dict[str, Any]] = None,
                              requested_by: Optional[str] = None) -> VerificationResult:
        """
        Validate the quality of output against specified criteria.
        
        Args:
            output_to_verify: Output that needs verification
            verification_criteria: Optional verification criteria
            requested_by: Optional ID of requesting worker
            
        Returns:
            VerificationResult instance
            
        Raises:
            WorkerError: If verification fails
        """
        if len(self.active_verifications) >= self.max_concurrent_verifications:
            raise WorkerError(
                f"Maximum concurrent verifications reached: {self.max_concurrent_verifications}",
                worker_id=self.worker_id,
                context={'active_verifications': len(self.active_verifications)}
            )
        
        try:
            # Create verification ID
            verification_id = str(uuid.uuid4())
            
            # Use provided criteria or defaults
            criteria = verification_criteria or self.default_criteria
            
            # Track active verification
            self.active_verifications[verification_id] = {
                'output': output_to_verify,
                'criteria': criteria,
                'requested_by': requested_by,
                'started_at': datetime.now()
            }
            
            # Perform quality assessment
            quality_assessment = self._assess_quality(output_to_verify, criteria)
            
            # Generate feedback
            feedback = self._generate_feedback(output_to_verify, quality_assessment, criteria)
            
            # Generate improvement suggestions
            suggestions = self._generate_improvement_suggestions(quality_assessment, criteria)
            
            # Determine verification status
            status = self._determine_verification_status(quality_assessment['overall_score'], criteria)
            
            # Create verification result
            result = VerificationResult(
                verification_id=verification_id,
                output_verified=output_to_verify,
                status=status,
                quality_level=quality_assessment['quality_level'],
                quality_score=quality_assessment['overall_score'],
                feedback=feedback,
                improvement_suggestions=suggestions,
                verification_criteria=criteria,
                verified_by=self.worker_id,
                verified_at=datetime.now(),
                details=quality_assessment['details']
            )
            
            # Store result and update metrics
            self.completed_verifications[verification_id] = result
            self._update_quality_metrics(result)
            
            # Remove from active verifications
            del self.active_verifications[verification_id]
            
            self.logger.info(f"Verification completed: {verification_id} - {status.value}")
            return result
            
        except Exception as e:
            # Clean up active verification
            if verification_id in self.active_verifications:
                del self.active_verifications[verification_id]
            
            self.logger.error(f"Verification failed: {e}")
            raise WorkerError(
                f"Output verification failed: {e}",
                worker_id=self.worker_id,
                context={'verification_id': verification_id, 'error': str(e)}
            )
    
    def provide_improvement_feedback(self, target_worker_id: str, verification_result: VerificationResult) -> bool:
        """
        Provide improvement feedback to a worker.
        
        Args:
            target_worker_id: ID of the worker to provide feedback to
            verification_result: Verification result containing feedback
            
        Returns:
            True if feedback was sent successfully
        """
        # Create feedback message
        message = {
            'message_type': MessageType.RESULT_REPORT.value,
            'verification_id': verification_result.verification_id,
            'verification_status': verification_result.status.value,
            'quality_level': verification_result.quality_level.value,
            'quality_score': verification_result.quality_score,
            'feedback': verification_result.feedback,
            'improvement_suggestions': verification_result.improvement_suggestions,
            'verified_by': self.worker_id,
            'verified_at': verification_result.verified_at.isoformat(),
            'requires_response': verification_result.status == VerificationStatus.NEEDS_REVISION
        }
        
        success = self.send_message_to_worker(target_worker_id, message)
        
        if success:
            self.logger.info(f"Feedback provided to {target_worker_id} for verification {verification_result.verification_id}")
        
        return success
    
    def approve_final_output(self, output: Any, approval_criteria: Optional[Dict[str, Any]] = None) -> bool:
        """
        Approve final output for delivery.
        
        Args:
            output: Output to approve
            approval_criteria: Optional approval criteria
            
        Returns:
            True if output is approved for final delivery
        """
        # Perform final verification
        verification_result = self.validate_output_quality(output, approval_criteria)
        
        # Check if output meets approval standards
        approved = (
            verification_result.status == VerificationStatus.APPROVED and
            verification_result.quality_score >= self.quality_threshold
        )
        
        if approved:
            self.logger.info(f"Output approved for final delivery - Quality: {verification_result.quality_level.value}")
        else:
            self.logger.warning(f"Output not approved - Status: {verification_result.status.value}, Score: {verification_result.quality_score}")
        
        return approved
    
    def maintain_quality_metrics(self) -> QualityMetrics:
        """
        Update and return current quality metrics.
        
        Returns:
            Current QualityMetrics instance
        """
        # Update metrics from recent verifications
        self.quality_metrics.last_updated = datetime.now()
        
        # Calculate improvement trends
        self._calculate_improvement_trends()
        
        # Update common issues
        self._update_common_issues()
        
        return self.quality_metrics
    
    def generate_quality_report(self, time_period_days: int = 30) -> Dict[str, Any]:
        """
        Generate a comprehensive quality report.
        
        Args:
            time_period_days: Number of days to include in report
            
        Returns:
            Dictionary containing quality report
        """
        cutoff_date = datetime.now() - timedelta(days=time_period_days)
        
        # Filter verifications by time period
        recent_verifications = [
            v for v in self.completed_verifications.values()
            if v.verified_at >= cutoff_date
        ]
        
        if not recent_verifications:
            return {
                'period_days': time_period_days,
                'total_verifications': 0,
                'message': 'No verifications in the specified period'
            }
        
        # Calculate report metrics
        total_verifications = len(recent_verifications)
        approved_count = len([v for v in recent_verifications if v.status == VerificationStatus.APPROVED])
        rejected_count = len([v for v in recent_verifications if v.status == VerificationStatus.REJECTED])
        
        average_score = sum(v.quality_score for v in recent_verifications) / total_verifications
        
        quality_distribution = {}
        for level in QualityLevel:
            quality_distribution[level.value] = len([v for v in recent_verifications if v.quality_level == level])
        
        return {
            'period_days': time_period_days,
            'total_verifications': total_verifications,
            'approval_rate': approved_count / total_verifications if total_verifications > 0 else 0,
            'rejection_rate': rejected_count / total_verifications if total_verifications > 0 else 0,
            'average_quality_score': average_score,
            'quality_distribution': quality_distribution,
            'quality_threshold': self.quality_threshold,
            'verifier_id': self.worker_id,
            'verifier_name': self.name,
            'generated_at': datetime.now().isoformat()
        }
    
    def get_verifier_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for this verifier.
        
        Returns:
            Dictionary containing verifier statistics
        """
        base_stats = self.get_collaboration_statistics()
        
        verifier_stats = {
            'active_verifications': len(self.active_verifications),
            'completed_verifications': len(self.completed_verifications),
            'quality_metrics': {
                'total_verifications': self.quality_metrics.total_verifications,
                'approved_count': self.quality_metrics.approved_count,
                'rejected_count': self.quality_metrics.rejected_count,
                'average_quality_score': self.quality_metrics.average_quality_score,
                'approval_rate': self.quality_metrics.approved_count / max(self.quality_metrics.total_verifications, 1)
            },
            'quality_threshold': self.quality_threshold,
            'strict_mode': self.strict_mode
        }
        
        return {**base_stats, **verifier_stats}
    
    def _assess_quality(self, output: Any, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the quality of output against criteria.
        
        Args:
            output: Output to assess
            criteria: Quality criteria
            
        Returns:
            Dictionary containing quality assessment
        """
        # Simplified quality assessment - can be enhanced with AI/ML
        assessment = {
            'criteria_scores': {},
            'overall_score': 0.0,
            'quality_level': QualityLevel.ACCEPTABLE,
            'details': {}
        }
        
        # Assess each criterion
        total_weight = 0
        weighted_score = 0
        
        for criterion, threshold in criteria.items():
            score = self._assess_criterion(output, criterion)
            weight = 1.0  # Equal weighting for now
            
            assessment['criteria_scores'][criterion] = score
            assessment['details'][criterion] = {
                'score': score,
                'threshold': threshold,
                'passed': score >= threshold
            }
            
            weighted_score += score * weight
            total_weight += weight
        
        # Calculate overall score
        assessment['overall_score'] = weighted_score / total_weight if total_weight > 0 else 0.0
        
        # Determine quality level
        assessment['quality_level'] = self._score_to_quality_level(assessment['overall_score'])
        
        return assessment
    
    def _assess_criterion(self, output: Any, criterion: str) -> float:
        """
        Assess a specific quality criterion.
        
        Args:
            output: Output to assess
            criterion: Criterion name
            
        Returns:
            Score between 0.0 and 1.0
        """
        # Simplified criterion assessment
        if criterion == 'accuracy':
            return self._assess_accuracy(output)
        elif criterion == 'completeness':
            return self._assess_completeness(output)
        elif criterion == 'clarity':
            return self._assess_clarity(output)
        elif criterion == 'format':
            return self._assess_format(output)
        else:
            # Default assessment for unknown criteria
            return 0.7
    
    def _assess_accuracy(self, output: Any) -> float:
        """Assess accuracy of output."""
        # Placeholder implementation
        if isinstance(output, dict) and output.get('task_completed'):
            return 0.8
        elif isinstance(output, str) and len(output) > 10:
            return 0.7
        else:
            return 0.5
    
    def _assess_completeness(self, output: Any) -> float:
        """Assess completeness of output."""
        # Placeholder implementation
        if isinstance(output, dict):
            required_fields = ['task_completed', 'description']
            present_fields = sum(1 for field in required_fields if field in output)
            return present_fields / len(required_fields)
        else:
            return 0.6
    
    def _assess_clarity(self, output: Any) -> float:
        """Assess clarity of output."""
        # Placeholder implementation
        if isinstance(output, dict) and 'description' in output:
            description = output['description']
            if isinstance(description, str) and len(description) > 20:
                return 0.8
        return 0.6
    
    def _assess_format(self, output: Any) -> float:
        """Assess format of output."""
        # Placeholder implementation
        if isinstance(output, dict):
            return 0.9
        elif isinstance(output, str):
            return 0.7
        else:
            return 0.5
    
    def _score_to_quality_level(self, score: float) -> QualityLevel:
        """Convert numeric score to quality level."""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.8:
            return QualityLevel.GOOD
        elif score >= 0.6:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.4:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    def _generate_feedback(self, output: Any, assessment: Dict[str, Any], criteria: Dict[str, Any]) -> List[str]:
        """Generate feedback based on quality assessment."""
        feedback = []
        
        # Check each criterion
        for criterion, details in assessment['details'].items():
            if not details['passed']:
                feedback.append(f"{criterion.title()} below threshold: {details['score']:.2f} < {details['threshold']:.2f}")
        
        # Overall feedback
        if assessment['overall_score'] < self.quality_threshold:
            feedback.append(f"Overall quality score {assessment['overall_score']:.2f} below threshold {self.quality_threshold}")
        
        # Positive feedback
        if assessment['quality_level'] in [QualityLevel.EXCELLENT, QualityLevel.GOOD]:
            feedback.append(f"Good quality output with {assessment['quality_level'].value} rating")
        
        return feedback
    
    def _generate_improvement_suggestions(self, assessment: Dict[str, Any], criteria: Dict[str, Any]) -> List[str]:
        """Generate improvement suggestions based on assessment."""
        suggestions = []
        
        # Suggestions based on failed criteria
        for criterion, details in assessment['details'].items():
            if not details['passed']:
                if criterion == 'accuracy':
                    suggestions.append("Verify facts and ensure correctness of information")
                elif criterion == 'completeness':
                    suggestions.append("Include all required information and address all aspects")
                elif criterion == 'clarity':
                    suggestions.append("Improve clarity and readability of the output")
                elif criterion == 'format':
                    suggestions.append("Follow proper formatting guidelines and structure")
        
        # General suggestions
        if assessment['overall_score'] < 0.7:
            suggestions.append("Consider reviewing the task requirements and improving overall quality")
        
        return suggestions
    
    def _determine_verification_status(self, quality_score: float, criteria: Dict[str, Any]) -> VerificationStatus:
        """Determine verification status based on quality score."""
        if quality_score >= self.quality_threshold:
            return VerificationStatus.APPROVED
        elif quality_score >= (self.quality_threshold * 0.8):
            return VerificationStatus.NEEDS_REVISION
        else:
            return VerificationStatus.REJECTED
    
    def _update_quality_metrics(self, result: VerificationResult) -> None:
        """Update quality metrics with new verification result."""
        self.quality_metrics.total_verifications += 1
        
        if result.status == VerificationStatus.APPROVED:
            self.quality_metrics.approved_count += 1
        elif result.status == VerificationStatus.REJECTED:
            self.quality_metrics.rejected_count += 1
        
        # Update average quality score
        total_score = (self.quality_metrics.average_quality_score * 
                      (self.quality_metrics.total_verifications - 1) + 
                      result.quality_score)
        self.quality_metrics.average_quality_score = total_score / self.quality_metrics.total_verifications
        
        # Update quality distribution
        self.quality_metrics.quality_distribution[result.quality_level] += 1
        
        self.quality_metrics.last_updated = datetime.now()
    
    def _calculate_improvement_trends(self) -> None:
        """Calculate improvement trends over time."""
        # Simplified trend calculation
        recent_verifications = list(self.completed_verifications.values())[-10:]  # Last 10 verifications
        
        if len(recent_verifications) >= 2:
            recent_avg = sum(v.quality_score for v in recent_verifications) / len(recent_verifications)
            overall_avg = self.quality_metrics.average_quality_score
            
            self.quality_metrics.improvement_trends['recent_vs_overall'] = recent_avg - overall_avg
    
    def _update_common_issues(self) -> None:
        """Update common issues based on recent feedback."""
        # Simplified common issues tracking
        issue_counts = {}
        
        for verification in list(self.completed_verifications.values())[-20:]:  # Last 20 verifications
            for feedback_item in verification.feedback:
                if feedback_item in issue_counts:
                    issue_counts[feedback_item] += 1
                else:
                    issue_counts[feedback_item] = 1
        
        # Convert to common issues format
        self.quality_metrics.common_issues = [
            {'issue': issue, 'frequency': count}
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
    
    def _setup_verifier_message_handlers(self) -> None:
        """Setup verifier-specific message handlers."""
        # Override verification request handler for verifier-specific behavior
        self.message_handlers[MessageType.VERIFICATION_REQUEST] = self._handle_verifier_verification_request
    
    def _handle_verifier_verification_request(self, message) -> None:
        """Handle verification request messages for verifiers."""
        execution_id = message.content.get('execution_id')
        output_to_verify = message.content.get('output_to_verify')
        verification_criteria = message.content.get('verification_criteria', {})
        requested_by = message.from_worker_id
        
        try:
            # Perform verification
            verification_result = self.validate_output_quality(
                output_to_verify=output_to_verify,
                verification_criteria=verification_criteria,
                requested_by=requested_by
            )
            
            # Send feedback to requesting worker
            if self.auto_feedback:
                self.provide_improvement_feedback(requested_by, verification_result)
            
            self.logger.info(f"Verification completed for {requested_by}: {verification_result.status.value}")
            
        except WorkerError as e:
            # Send error response
            error_message = {
                'message_type': MessageType.ERROR_NOTIFICATION.value,
                'execution_id': execution_id,
                'error_details': {
                    'error_message': str(e),
                    'error_type': 'verification_failed',
                    'timestamp': datetime.now().isoformat()
                },
                'verifier_id': self.worker_id
            }
            
            self.send_message_to_worker(requested_by, error_message)
            self.logger.error(f"Verification failed: {e}")


# Import timedelta for quality report
from datetime import timedelta
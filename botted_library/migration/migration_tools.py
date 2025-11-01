"""
Migration Tools for Botted Library v1 to v2

Provides automated tools to analyze, migrate, and validate the transition
from v1 to v2 functionality.
"""

import os
import json
import ast
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class MigrationIssue:
    """Represents a migration issue or recommendation."""
    severity: str  # 'error', 'warning', 'info'
    category: str  # 'compatibility', 'performance', 'feature'
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class MigrationReport:
    """Complete migration analysis report."""
    project_path: str
    analysis_date: datetime
    v1_usage_found: bool
    issues: List[MigrationIssue]
    recommendations: List[str]
    compatibility_score: float
    estimated_migration_time: str


class MigrationAnalyzer:
    """Analyzes existing code for v1 usage and migration opportunities."""
    
    def __init__(self):
        self.logger = logging.getLogger("MigrationAnalyzer")
        
    def analyze_project(self, project_path: str) -> MigrationReport:
        """
        Analyze a project for v1 usage and migration opportunities.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            MigrationReport with analysis results
        """
        issues = []
        recommendations = []
        v1_usage_found = False
        
        # Scan Python files for v1 usage patterns
        python_files = self._find_python_files(project_path)
        
        for file_path in python_files:
            file_issues, file_v1_usage = self._analyze_file(file_path)
            issues.extend(file_issues)
            if file_v1_usage:
                v1_usage_found = True
        
        # Generate recommendations based on findings
        recommendations = self._generate_recommendations(issues, v1_usage_found)
        
        # Calculate compatibility score
        compatibility_score = self._calculate_compatibility_score(issues)
        
        # Estimate migration time
        estimated_time = self._estimate_migration_time(issues, v1_usage_found)
        
        return MigrationReport(
            project_path=project_path,
            analysis_date=datetime.now(),
            v1_usage_found=v1_usage_found,
            issues=issues,
            recommendations=recommendations,
            compatibility_score=compatibility_score,
            estimated_migration_time=estimated_time
        )
    
    def _find_python_files(self, project_path: str) -> List[str]:
        """Find all Python files in the project."""
        python_files = []
        
        for root, dirs, files in os.walk(project_path):
            # Skip common directories that don't need analysis
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.pytest_cache', 'venv', '.venv']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def _analyze_file(self, file_path: str) -> Tuple[List[MigrationIssue], bool]:
        """Analyze a single Python file for v1 usage."""
        issues = []
        v1_usage_found = False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST to find imports and function calls
            try:
                tree = ast.parse(content)
                issues_from_ast, v1_from_ast = self._analyze_ast(tree, file_path)
                issues.extend(issues_from_ast)
                if v1_from_ast:
                    v1_usage_found = True
            except SyntaxError:
                issues.append(MigrationIssue(
                    severity='warning',
                    category='compatibility',
                    message='Could not parse file - syntax error',
                    file_path=file_path
                ))
            
            # Use regex patterns for additional analysis
            regex_issues, v1_from_regex = self._analyze_with_regex(content, file_path)
            issues.extend(regex_issues)
            if v1_from_regex:
                v1_usage_found = True
                
        except Exception as e:
            issues.append(MigrationIssue(
                severity='error',
                category='compatibility',
                message=f'Could not analyze file: {e}',
                file_path=file_path
            ))
        
        return issues, v1_usage_found
    
    def _analyze_ast(self, tree: ast.AST, file_path: str) -> Tuple[List[MigrationIssue], bool]:
        """Analyze AST for v1 patterns."""
        issues = []
        v1_usage_found = False
        
        class V1UsageVisitor(ast.NodeVisitor):
            def __init__(self):
                self.issues = []
                self.v1_found = False
            
            def visit_Import(self, node):
                for alias in node.names:
                    if 'botted_library' in alias.name:
                        self.v1_found = True
                        self.issues.append(MigrationIssue(
                            severity='info',
                            category='feature',
                            message='Found botted_library import - can benefit from v2 features',
                            file_path=file_path,
                            line_number=node.lineno,
                            suggestion='Import now automatically includes collaborative features'
                        ))
                self.generic_visit(node)
            
            def visit_ImportFrom(self, node):
                if node.module and 'botted_library' in node.module:
                    self.v1_found = True
                    
                    # Check for specific v1 imports
                    for alias in node.names:
                        if alias.name in ['create_worker', 'Worker']:
                            self.issues.append(MigrationIssue(
                                severity='info',
                                category='feature',
                                message=f'Found v1 {alias.name} import - now includes collaborative features',
                                file_path=file_path,
                                line_number=node.lineno,
                                suggestion='No changes needed - collaborative features enabled automatically'
                            ))
                        elif alias.name == 'simple_worker':
                            self.issues.append(MigrationIssue(
                                severity='warning',
                                category='compatibility',
                                message='Direct simple_worker import found',
                                file_path=file_path,
                                line_number=node.lineno,
                                suggestion='Consider using main botted_library import for better compatibility'
                            ))
                
                self.generic_visit(node)
            
            def visit_Call(self, node):
                # Check for create_worker calls
                if (isinstance(node.func, ast.Name) and node.func.id == 'create_worker') or \
                   (isinstance(node.func, ast.Attribute) and node.func.attr == 'create_worker'):
                    self.v1_found = True
                    self.issues.append(MigrationIssue(
                        severity='info',
                        category='feature',
                        message='Found create_worker call - can now use collaborative features',
                        file_path=file_path,
                        line_number=node.lineno,
                        suggestion='Worker can now delegate tasks and collaborate with other workers'
                    ))
                
                # Check for worker.call() method calls
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'call':
                    self.issues.append(MigrationIssue(
                        severity='info',
                        category='feature',
                        message='Found worker.call() - can benefit from collaborative context',
                        file_path=file_path,
                        line_number=node.lineno,
                        suggestion='Tasks can now automatically use collaboration when beneficial'
                    ))
                
                self.generic_visit(node)
        
        visitor = V1UsageVisitor()
        visitor.visit(tree)
        
        return visitor.issues, visitor.v1_found
    
    def _analyze_with_regex(self, content: str, file_path: str) -> Tuple[List[MigrationIssue], bool]:
        """Use regex patterns to find additional v1 usage."""
        issues = []
        v1_usage_found = False
        
        # Pattern for worker configuration
        config_pattern = r'config\s*=\s*\{[^}]*["\']llm["\'][^}]*\}'
        if re.search(config_pattern, content):
            v1_usage_found = True
            issues.append(MigrationIssue(
                severity='info',
                category='feature',
                message='Found worker configuration - can be enhanced for collaborative features',
                file_path=file_path,
                suggestion='Consider adding collaborative server configuration options'
            ))
        
        # Pattern for manual worker management
        if re.search(r'worker\.shutdown\(\)', content):
            issues.append(MigrationIssue(
                severity='info',
                category='feature',
                message='Found manual worker shutdown - server manages lifecycle in v2',
                file_path=file_path,
                suggestion='Server automatically manages worker lifecycle in collaborative mode'
            ))
        
        return issues, v1_usage_found
    
    def _generate_recommendations(self, issues: List[MigrationIssue], v1_usage_found: bool) -> List[str]:
        """Generate migration recommendations based on analysis."""
        recommendations = []
        
        if not v1_usage_found:
            recommendations.append("No v1 usage detected - project is ready for v2 features")
            recommendations.append("Consider using botted_library.create_worker() to create collaborative workers")
            return recommendations
        
        # Count issue types
        error_count = len([i for i in issues if i.severity == 'error'])
        warning_count = len([i for i in issues if i.severity == 'warning'])
        
        if error_count == 0:
            recommendations.append("✅ No blocking issues found - migration should be smooth")
        else:
            recommendations.append(f"⚠️ {error_count} errors need to be resolved before migration")
        
        if warning_count > 0:
            recommendations.append(f"📋 {warning_count} warnings should be reviewed for optimal migration")
        
        # Specific recommendations based on patterns
        feature_issues = [i for i in issues if i.category == 'feature']
        if feature_issues:
            recommendations.append("🚀 Your code can benefit from new collaborative features:")
            recommendations.append("   - Workers can now delegate tasks to other workers")
            recommendations.append("   - Shared whiteboards and file systems available")
            recommendations.append("   - Automatic load balancing and worker management")
        
        recommendations.append("📖 Run migration guide for step-by-step instructions")
        
        return recommendations
    
    def _calculate_compatibility_score(self, issues: List[MigrationIssue]) -> float:
        """Calculate a compatibility score (0.0 to 1.0)."""
        if not issues:
            return 1.0
        
        error_count = len([i for i in issues if i.severity == 'error'])
        warning_count = len([i for i in issues if i.severity == 'warning'])
        
        # Errors significantly impact score, warnings less so
        penalty = (error_count * 0.3) + (warning_count * 0.1)
        score = max(0.0, 1.0 - penalty)
        
        return round(score, 2)
    
    def _estimate_migration_time(self, issues: List[MigrationIssue], v1_usage_found: bool) -> str:
        """Estimate migration time based on complexity."""
        if not v1_usage_found:
            return "Immediate - no v1 usage detected"
        
        error_count = len([i for i in issues if i.severity == 'error'])
        warning_count = len([i for i in issues if i.severity == 'warning'])
        
        if error_count == 0 and warning_count == 0:
            return "Immediate - fully compatible"
        elif error_count == 0 and warning_count <= 3:
            return "15-30 minutes - minor adjustments"
        elif error_count <= 2:
            return "1-2 hours - some fixes needed"
        else:
            return "Half day - significant changes required"


class ConfigMigrator:
    """Migrates configuration from v1 to v2 format."""
    
    def migrate_config(self, v1_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate v1 configuration to v2 format.
        
        Args:
            v1_config: Original v1 configuration
            
        Returns:
            Migrated v2 configuration with collaborative features
        """
        v2_config = v1_config.copy()
        
        # Add collaborative server configuration
        if 'collaborative_server' not in v2_config:
            v2_config['collaborative_server'] = {
                'enabled': True,
                'auto_start': True,
                'host': 'localhost',
                'port': 8765,
                'max_workers': 100
            }
        
        # Migrate LLM configuration
        if 'llm' in v1_config:
            llm_config = v1_config['llm'].copy()
            # Add collaborative context settings
            llm_config['collaborative_context'] = True
            llm_config['worker_communication'] = True
            v2_config['llm'] = llm_config
        
        # Add worker type configuration
        if 'worker_type' not in v2_config:
            v2_config['worker_type'] = 'executor'  # Default for v1 workers
        
        # Add collaboration settings
        v2_config['collaboration'] = {
            'auto_delegate': False,  # Conservative default
            'share_memory': True,
            'join_spaces': True
        }
        
        return v2_config


class WorkerMigrator:
    """Migrates worker instances from v1 to v2."""
    
    def __init__(self):
        self.logger = logging.getLogger("WorkerMigrator")
    
    def migrate_worker_to_v2(self, v1_worker, worker_type: str = 'executor') -> 'EnhancedWorker':
        """
        Migrate a v1 worker to a v2 enhanced worker.
        
        Args:
            v1_worker: V1 worker instance
            worker_type: Type for the v2 worker ('executor', 'planner', 'verifier')
            
        Returns:
            Enhanced v2 worker instance
        """
        from ..core.enhanced_worker import EnhancedWorker
        from ..core.enhanced_worker_registry import WorkerType
        from ..core.collaborative_server import get_global_server
        
        # Map string to WorkerType enum
        type_mapping = {
            'executor': WorkerType.EXECUTOR,
            'planner': WorkerType.PLANNER,
            'verifier': WorkerType.VERIFIER
        }
        
        worker_type_enum = type_mapping.get(worker_type.lower(), WorkerType.EXECUTOR)
        
        # Create enhanced worker with v1 worker's properties
        enhanced_worker = EnhancedWorker(
            name=v1_worker.name,
            role=v1_worker.role,
            worker_type=worker_type_enum,
            server_connection=get_global_server()
        )
        
        # Migrate configuration
        enhanced_worker.config = v1_worker.config.copy()
        
        # Migrate task history if available
        if hasattr(v1_worker, '_task_history'):
            enhanced_worker._task_history = v1_worker._task_history.copy()
        
        self.logger.info(f"Migrated worker {v1_worker.name} from v1 to v2 ({worker_type})")
        
        return enhanced_worker


def validate_migration(project_path: str) -> Dict[str, Any]:
    """
    Validate that a migration was successful.
    
    Args:
        project_path: Path to the migrated project
        
    Returns:
        Validation results
    """
    analyzer = MigrationAnalyzer()
    report = analyzer.analyze_project(project_path)
    
    validation_results = {
        'migration_successful': True,
        'issues_found': len(report.issues),
        'compatibility_score': report.compatibility_score,
        'blocking_issues': [i for i in report.issues if i.severity == 'error'],
        'warnings': [i for i in report.issues if i.severity == 'warning'],
        'recommendations': report.recommendations
    }
    
    # Check if migration was successful
    if validation_results['blocking_issues']:
        validation_results['migration_successful'] = False
    
    return validation_results


def create_migration_report(project_path: str, output_file: Optional[str] = None) -> str:
    """
    Create a comprehensive migration report.
    
    Args:
        project_path: Path to analyze
        output_file: Optional file to save report to
        
    Returns:
        Report content as string
    """
    analyzer = MigrationAnalyzer()
    report = analyzer.analyze_project(project_path)
    
    # Generate report content
    report_content = f"""
# Botted Library v1 to v2 Migration Report

**Project:** {report.project_path}
**Analysis Date:** {report.analysis_date.strftime('%Y-%m-%d %H:%M:%S')}
**Compatibility Score:** {report.compatibility_score}/1.0
**Estimated Migration Time:** {report.estimated_migration_time}

## Summary

{'✅ V1 usage detected' if report.v1_usage_found else '❌ No v1 usage found'}
- **Issues Found:** {len(report.issues)}
- **Errors:** {len([i for i in report.issues if i.severity == 'error'])}
- **Warnings:** {len([i for i in report.issues if i.severity == 'warning'])}

## Issues and Recommendations

"""
    
    # Add issues by category
    for category in ['error', 'warning', 'info']:
        category_issues = [i for i in report.issues if i.severity == category]
        if category_issues:
            report_content += f"\n### {category.title()}s\n\n"
            for issue in category_issues:
                report_content += f"- **{issue.message}**\n"
                if issue.file_path:
                    report_content += f"  - File: {issue.file_path}"
                    if issue.line_number:
                        report_content += f" (line {issue.line_number})"
                    report_content += "\n"
                if issue.suggestion:
                    report_content += f"  - Suggestion: {issue.suggestion}\n"
                report_content += "\n"
    
    # Add recommendations
    if report.recommendations:
        report_content += "\n## Migration Recommendations\n\n"
        for rec in report.recommendations:
            report_content += f"- {rec}\n"
    
    # Add next steps
    report_content += """
## Next Steps

1. **Review Issues:** Address any errors and warnings listed above
2. **Test Compatibility:** Run your existing code to ensure it works with v2
3. **Explore New Features:** Try collaborative features like worker delegation
4. **Update Documentation:** Update any documentation to reflect v2 capabilities

## Getting Help

- Run `botted_library.migration.print_migration_steps()` for detailed migration guide
- Check the v2 documentation for new collaborative features
- Use `botted_library.compatibility.get_compatibility_status()` to monitor migration
"""
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
    
    return report_content
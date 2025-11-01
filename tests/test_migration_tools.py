"""
Tests for Migration Tools

Tests the migration analysis, configuration migration, and validation tools.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from botted_library.migration.migration_tools import (
    MigrationAnalyzer,
    ConfigMigrator,
    WorkerMigrator,
    MigrationIssue,
    MigrationReport,
    validate_migration,
    create_migration_report
)


class TestMigrationAnalyzer:
    """Test the MigrationAnalyzer class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.analyzer = MigrationAnalyzer()
    
    def test_analyze_project_with_v1_usage(self):
        """Test analyzing a project with v1 usage."""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test Python file with v1 usage
            test_file = os.path.join(temp_dir, "test_worker.py")
            with open(test_file, 'w') as f:
                f.write("""
from botted_library import create_worker

worker = create_worker("Test", "Role", "Description")
result = worker.call("Do something")
""")
            
            report = self.analyzer.analyze_project(temp_dir)
            
            assert isinstance(report, MigrationReport)
            assert report.v1_usage_found is True
            assert report.project_path == temp_dir
            assert len(report.issues) > 0
            assert report.compatibility_score >= 0.0
            assert report.compatibility_score <= 1.0
    
    def test_analyze_project_without_v1_usage(self):
        """Test analyzing a project without v1 usage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test Python file without v1 usage
            test_file = os.path.join(temp_dir, "other_code.py")
            with open(test_file, 'w') as f:
                f.write("""
import requests

def fetch_data():
    return requests.get("https://api.example.com")
""")
            
            report = self.analyzer.analyze_project(temp_dir)
            
            assert report.v1_usage_found is False
            assert len([i for i in report.issues if 'botted_library' in i.message]) == 0
    
    def test_find_python_files(self):
        """Test finding Python files in project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create various files
            py_file1 = os.path.join(temp_dir, "main.py")
            py_file2 = os.path.join(temp_dir, "utils.py")
            txt_file = os.path.join(temp_dir, "readme.txt")
            
            # Create subdirectory with Python file
            sub_dir = os.path.join(temp_dir, "subdir")
            os.makedirs(sub_dir)
            py_file3 = os.path.join(sub_dir, "module.py")
            
            # Create files
            for file_path in [py_file1, py_file2, txt_file, py_file3]:
                with open(file_path, 'w') as f:
                    f.write("# Test file")
            
            python_files = self.analyzer._find_python_files(temp_dir)
            
            assert len(python_files) == 3
            assert py_file1 in python_files
            assert py_file2 in python_files
            assert py_file3 in python_files
            assert txt_file not in python_files
    
    def test_analyze_file_with_v1_imports(self):
        """Test analyzing a file with v1 imports."""
        test_content = """
from botted_library import create_worker
from botted_library.simple_worker import Worker

worker = create_worker("Test", "Role", "Description")
result = worker.call("Task")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_content)
            f.flush()
            
            try:
                issues, v1_usage = self.analyzer._analyze_file(f.name)
                
                assert v1_usage is True
                assert len(issues) > 0
                
                # Check for specific issue types
                import_issues = [i for i in issues if 'import' in i.message.lower()]
                call_issues = [i for i in issues if 'call' in i.message.lower()]
                
                assert len(import_issues) > 0
                assert len(call_issues) > 0
                
            finally:
                os.unlink(f.name)
    
    def test_analyze_file_with_syntax_error(self):
        """Test analyzing a file with syntax errors."""
        test_content = """
from botted_library import create_worker
def invalid_syntax(
    # Missing closing parenthesis
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_content)
            f.flush()
            
            try:
                issues, v1_usage = self.analyzer._analyze_file(f.name)
                
                # Should handle syntax error gracefully
                syntax_errors = [i for i in issues if 'syntax error' in i.message.lower()]
                assert len(syntax_errors) > 0
                
            finally:
                os.unlink(f.name)
    
    def test_calculate_compatibility_score(self):
        """Test compatibility score calculation."""
        # No issues - perfect score
        assert self.analyzer._calculate_compatibility_score([]) == 1.0
        
        # Only info issues - high score
        info_issues = [
            MigrationIssue('info', 'feature', 'Info message'),
            MigrationIssue('info', 'feature', 'Another info')
        ]
        score = self.analyzer._calculate_compatibility_score(info_issues)
        assert score == 1.0  # Info issues don't affect score
        
        # Warning issues - reduced score
        warning_issues = [
            MigrationIssue('warning', 'compatibility', 'Warning message')
        ]
        score = self.analyzer._calculate_compatibility_score(warning_issues)
        assert score == 0.9  # 0.1 penalty for warning
        
        # Error issues - significant penalty
        error_issues = [
            MigrationIssue('error', 'compatibility', 'Error message')
        ]
        score = self.analyzer._calculate_compatibility_score(error_issues)
        assert score == 0.7  # 0.3 penalty for error
    
    def test_estimate_migration_time(self):
        """Test migration time estimation."""
        # No v1 usage
        time_estimate = self.analyzer._estimate_migration_time([], False)
        assert "Immediate" in time_estimate
        
        # V1 usage but no issues
        time_estimate = self.analyzer._estimate_migration_time([], True)
        assert "Immediate" in time_estimate
        
        # Minor warnings
        warning_issues = [MigrationIssue('warning', 'compatibility', 'Warning')]
        time_estimate = self.analyzer._estimate_migration_time(warning_issues, True)
        assert "15-30 minutes" in time_estimate
        
        # Errors present
        error_issues = [
            MigrationIssue('error', 'compatibility', 'Error 1'),
            MigrationIssue('error', 'compatibility', 'Error 2')
        ]
        time_estimate = self.analyzer._estimate_migration_time(error_issues, True)
        assert "1-2 hours" in time_estimate


class TestConfigMigrator:
    """Test the ConfigMigrator class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.migrator = ConfigMigrator()
    
    def test_migrate_basic_config(self):
        """Test migrating basic v1 configuration."""
        v1_config = {
            'llm': {'provider': 'openai', 'model': 'gpt-4'},
            'browser': {'headless': True}
        }
        
        v2_config = self.migrator.migrate_config(v1_config)
        
        # Verify original config is preserved
        assert v2_config['llm']['provider'] == 'openai'
        assert v2_config['browser']['headless'] is True
        
        # Verify collaborative features are added
        assert 'collaborative_server' in v2_config
        assert v2_config['collaborative_server']['enabled'] is True
        assert 'collaboration' in v2_config
        assert 'worker_type' in v2_config
    
    def test_migrate_config_with_existing_collaborative_settings(self):
        """Test migrating config that already has some collaborative settings."""
        v1_config = {
            'llm': {'provider': 'gemini'},
            'collaborative_server': {'port': 9000}  # Custom setting
        }
        
        v2_config = self.migrator.migrate_config(v1_config)
        
        # Verify existing collaborative settings are preserved
        assert v2_config['collaborative_server']['port'] == 9000
        # But other defaults are still added
        assert v2_config['collaborative_server']['enabled'] is True
    
    def test_migrate_llm_config_enhancement(self):
        """Test that LLM config is enhanced with collaborative features."""
        v1_config = {
            'llm': {
                'provider': 'openai',
                'temperature': 0.7,
                'max_tokens': 1000
            }
        }
        
        v2_config = self.migrator.migrate_config(v1_config)
        
        # Verify original LLM settings preserved
        assert v2_config['llm']['provider'] == 'openai'
        assert v2_config['llm']['temperature'] == 0.7
        assert v2_config['llm']['max_tokens'] == 1000
        
        # Verify collaborative enhancements added
        assert v2_config['llm']['collaborative_context'] is True
        assert v2_config['llm']['worker_communication'] is True
    
    def test_migrate_empty_config(self):
        """Test migrating empty configuration."""
        v1_config = {}
        
        v2_config = self.migrator.migrate_config(v1_config)
        
        # Verify all v2 defaults are added
        assert 'collaborative_server' in v2_config
        assert 'worker_type' in v2_config
        assert 'collaboration' in v2_config
        assert v2_config['worker_type'] == 'executor'


class TestWorkerMigrator:
    """Test the WorkerMigrator class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.migrator = WorkerMigrator()
    
    @patch('botted_library.migration.migration_tools.EnhancedWorker')
    @patch('botted_library.migration.migration_tools.get_global_server')
    def test_migrate_worker_to_v2(self, mock_get_server, mock_enhanced_worker):
        """Test migrating a v1 worker to v2."""
        # Mock v1 worker
        mock_v1_worker = Mock()
        mock_v1_worker.name = "TestWorker"
        mock_v1_worker.role = "Test Role"
        mock_v1_worker.config = {'llm': {'provider': 'test'}}
        mock_v1_worker._task_history = [{'task': 'Previous task'}]
        
        # Mock v2 components
        mock_server = Mock()
        mock_get_server.return_value = mock_server
        
        mock_v2_worker = Mock()
        mock_enhanced_worker.return_value = mock_v2_worker
        
        # Perform migration
        result = self.migrator.migrate_worker_to_v2(mock_v1_worker, 'executor')
        
        # Verify EnhancedWorker was created with correct parameters
        mock_enhanced_worker.assert_called_once()
        call_args = mock_enhanced_worker.call_args
        assert call_args[1]['name'] == "TestWorker"
        assert call_args[1]['role'] == "Test Role"
        
        # Verify configuration was migrated
        assert mock_v2_worker.config == {'llm': {'provider': 'test'}}
        
        # Verify task history was migrated
        assert mock_v2_worker._task_history == [{'task': 'Previous task'}]
    
    @patch('botted_library.migration.migration_tools.EnhancedWorker')
    @patch('botted_library.migration.migration_tools.get_global_server')
    def test_migrate_worker_different_types(self, mock_get_server, mock_enhanced_worker):
        """Test migrating workers to different v2 types."""
        mock_v1_worker = Mock()
        mock_v1_worker.name = "TestWorker"
        mock_v1_worker.role = "Test Role"
        mock_v1_worker.config = {}
        
        mock_server = Mock()
        mock_get_server.return_value = mock_server
        mock_enhanced_worker.return_value = Mock()
        
        # Test different worker types
        for worker_type in ['executor', 'planner', 'verifier']:
            self.migrator.migrate_worker_to_v2(mock_v1_worker, worker_type)
            
            # Verify correct WorkerType was used
            call_args = mock_enhanced_worker.call_args
            worker_type_arg = call_args[1]['worker_type']
            assert worker_type.upper() in str(worker_type_arg)


class TestMigrationValidation:
    """Test migration validation functions."""
    
    def test_validate_migration_success(self):
        """Test successful migration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file with no blocking issues
            test_file = os.path.join(temp_dir, "test.py")
            with open(test_file, 'w') as f:
                f.write("print('Hello world')")  # No v1 usage
            
            with patch('botted_library.migration.migration_tools.MigrationAnalyzer') as mock_analyzer:
                mock_report = Mock()
                mock_report.issues = [
                    MigrationIssue('info', 'feature', 'Info message')
                ]
                mock_report.compatibility_score = 1.0
                mock_report.recommendations = ['All good']
                
                mock_analyzer.return_value.analyze_project.return_value = mock_report
                
                result = validate_migration(temp_dir)
                
                assert result['migration_successful'] is True
                assert result['issues_found'] == 1
                assert result['compatibility_score'] == 1.0
                assert len(result['blocking_issues']) == 0
    
    def test_validate_migration_with_errors(self):
        """Test migration validation with blocking errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('botted_library.migration.migration_tools.MigrationAnalyzer') as mock_analyzer:
                mock_report = Mock()
                mock_report.issues = [
                    MigrationIssue('error', 'compatibility', 'Blocking error'),
                    MigrationIssue('warning', 'compatibility', 'Warning')
                ]
                mock_report.compatibility_score = 0.5
                mock_report.recommendations = ['Fix errors']
                
                mock_analyzer.return_value.analyze_project.return_value = mock_report
                
                result = validate_migration(temp_dir)
                
                assert result['migration_successful'] is False
                assert len(result['blocking_issues']) == 1
                assert len(result['warnings']) == 1
                assert result['blocking_issues'][0].severity == 'error'
    
    def test_create_migration_report(self):
        """Test creating migration report."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('botted_library.migration.migration_tools.MigrationAnalyzer') as mock_analyzer:
                mock_report = Mock()
                mock_report.project_path = temp_dir
                mock_report.analysis_date = datetime(2024, 1, 1, 12, 0, 0)
                mock_report.v1_usage_found = True
                mock_report.compatibility_score = 0.8
                mock_report.estimated_migration_time = "30 minutes"
                mock_report.issues = [
                    MigrationIssue('warning', 'compatibility', 'Test warning', 'test.py', 10, 'Fix this')
                ]
                mock_report.recommendations = ['Test recommendation']
                
                mock_analyzer.return_value.analyze_project.return_value = mock_report
                
                report_content = create_migration_report(temp_dir)
                
                # Verify report content
                assert "Migration Report" in report_content
                assert temp_dir in report_content
                assert "0.8/1.0" in report_content
                assert "30 minutes" in report_content
                assert "Test warning" in report_content
                assert "Test recommendation" in report_content
    
    def test_create_migration_report_with_file_output(self):
        """Test creating migration report with file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "migration_report.md")
            
            with patch('botted_library.migration.migration_tools.MigrationAnalyzer') as mock_analyzer:
                mock_report = Mock()
                mock_report.project_path = temp_dir
                mock_report.analysis_date = datetime.now()
                mock_report.v1_usage_found = False
                mock_report.compatibility_score = 1.0
                mock_report.estimated_migration_time = "Immediate"
                mock_report.issues = []
                mock_report.recommendations = []
                
                mock_analyzer.return_value.analyze_project.return_value = mock_report
                
                report_content = create_migration_report(temp_dir, output_file)
                
                # Verify file was created
                assert os.path.exists(output_file)
                
                # Verify file content matches returned content
                with open(output_file, 'r') as f:
                    file_content = f.read()
                
                assert file_content == report_content
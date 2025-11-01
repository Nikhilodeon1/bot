"""
Tests for Migration Guide

Tests the migration guide functionality and readiness checks.
"""

import pytest
import sys
from unittest.mock import Mock, patch
from io import StringIO

from botted_library.migration.migration_guide import (
    get_migration_guide,
    print_migration_steps,
    check_migration_readiness,
    print_migration_readiness
)


class TestMigrationGuide:
    """Test the migration guide functionality."""
    
    def test_get_migration_guide_structure(self):
        """Test that migration guide has correct structure."""
        guide = get_migration_guide()
        
        # Verify main sections exist
        assert 'overview' in guide
        assert 'quick_start' in guide
        assert 'migration_steps' in guide
        assert 'troubleshooting' in guide
        assert 'best_practices' in guide
        assert 'new_features' in guide
        
        # Verify overview section
        overview = guide['overview']
        assert 'title' in overview
        assert 'description' in overview
        assert 'compatibility' in overview
        assert 'v1 to v2' in overview['title']
        assert 'backward compatible' in overview['compatibility']
        
        # Verify quick start section
        quick_start = guide['quick_start']
        assert 'title' in quick_start
        assert 'steps' in quick_start
        assert isinstance(quick_start['steps'], list)
        assert len(quick_start['steps']) > 0
    
    def test_migration_steps_structure(self):
        """Test that migration steps have correct structure."""
        guide = get_migration_guide()
        steps = guide['migration_steps']
        
        assert isinstance(steps, list)
        assert len(steps) >= 4  # Should have at least 4 main steps
        
        for i, step in enumerate(steps):
            assert 'step' in step
            assert 'title' in step
            assert 'description' in step
            assert 'actions' in step
            assert 'code_example' in step
            
            assert step['step'] == i + 1  # Steps should be numbered sequentially
            assert isinstance(step['actions'], list)
            assert len(step['actions']) > 0
            assert isinstance(step['code_example'], str)
            assert len(step['code_example']) > 0
    
    def test_troubleshooting_section(self):
        """Test troubleshooting section structure."""
        guide = get_migration_guide()
        troubleshooting = guide['troubleshooting']
        
        assert 'common_issues' in troubleshooting
        issues = troubleshooting['common_issues']
        
        assert isinstance(issues, list)
        assert len(issues) > 0
        
        for issue in issues:
            assert 'issue' in issue
            assert 'solution' in issue
            assert 'check' in issue
            assert isinstance(issue['issue'], str)
            assert isinstance(issue['solution'], str)
            assert isinstance(issue['check'], str)
    
    def test_new_features_section(self):
        """Test new features section."""
        guide = get_migration_guide()
        features = guide['new_features']
        
        assert isinstance(features, dict)
        assert len(features) > 0
        
        # Check for expected v2 features
        expected_features = [
            'collaborative_workers',
            'shared_resources', 
            'worker_specialization',
            'automatic_server'
        ]
        
        for feature in expected_features:
            assert feature in features
            assert isinstance(features[feature], str)
            assert len(features[feature]) > 0
    
    def test_best_practices_section(self):
        """Test best practices section."""
        guide = get_migration_guide()
        practices = guide['best_practices']
        
        assert isinstance(practices, list)
        assert len(practices) > 0
        
        for practice in practices:
            assert isinstance(practice, str)
            assert len(practice) > 0
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_print_migration_steps(self, mock_stdout):
        """Test printing migration steps to console."""
        print_migration_steps()
        
        output = mock_stdout.getvalue()
        
        # Verify key sections are printed
        assert "Migration Report" in output or "Migration Guide" in output
        assert "Step" in output or "step" in output
        assert "New Features" in output or "features" in output
        assert "Best Practices" in output or "practices" in output
        assert "Troubleshooting" in output or "troubleshooting" in output
        
        # Verify formatting elements
        assert "=" in output  # Header separators
        assert "-" in output  # Section separators
        assert "•" in output or "*" in output  # Bullet points


class TestMigrationReadiness:
    """Test migration readiness checking functionality."""
    
    def test_check_migration_readiness_success(self):
        """Test successful readiness check."""
        with patch('sys.version_info', (3, 8, 0)):  # Mock Python 3.8
            with patch('botted_library.migration.migration_guide.botted_library') as mock_lib:
                mock_lib.__version__ = "2.0.0"
                
                with patch('botted_library.migration.migration_guide.CollaborativeServer'):
                    readiness = check_migration_readiness()
                    
                    assert readiness['ready'] is True
                    assert readiness['botted_library_available'] is True
                    assert readiness['collaborative_server_available'] is True
                    assert len(readiness['issues']) == 0
                    assert "ready for migration" in ' '.join(readiness['recommendations']).lower()
    
    def test_check_migration_readiness_old_python(self):
        """Test readiness check with old Python version."""
        with patch('sys.version_info', (3, 6, 0)):  # Mock Python 3.6
            readiness = check_migration_readiness()
            
            assert readiness['ready'] is False
            python_issues = [i for i in readiness['issues'] if 'Python' in i]
            assert len(python_issues) > 0
            assert "3.7+" in python_issues[0]
    
    def test_check_migration_readiness_no_botted_library(self):
        """Test readiness check without botted_library installed."""
        with patch('sys.version_info', (3, 8, 0)):
            with patch('botted_library.migration.migration_guide.botted_library', side_effect=ImportError):
                readiness = check_migration_readiness()
                
                assert readiness['ready'] is False
                assert readiness['botted_library_available'] is False
                
                lib_issues = [i for i in readiness['issues'] if 'botted_library' in i]
                assert len(lib_issues) > 0
    
    def test_check_migration_readiness_no_collaborative_server(self):
        """Test readiness check without collaborative server components."""
        with patch('sys.version_info', (3, 8, 0)):
            with patch('botted_library.migration.migration_guide.botted_library') as mock_lib:
                mock_lib.__version__ = "2.0.0"
                
                with patch('botted_library.migration.migration_guide.CollaborativeServer', side_effect=ImportError):
                    readiness = check_migration_readiness()
                    
                    assert readiness['collaborative_server_available'] is False
                    
                    server_issues = [i for i in readiness['issues'] if 'Collaborative server' in i]
                    assert len(server_issues) > 0
    
    def test_check_migration_readiness_python_version_info(self):
        """Test that Python version is correctly captured."""
        readiness = check_migration_readiness()
        
        assert 'python_version' in readiness
        assert isinstance(readiness['python_version'], str)
        assert len(readiness['python_version']) > 0
        # Should contain version numbers
        assert any(char.isdigit() for char in readiness['python_version'])
    
    def test_check_migration_readiness_recommendations(self):
        """Test that appropriate recommendations are generated."""
        # Test ready state
        with patch('sys.version_info', (3, 8, 0)):
            with patch('botted_library.migration.migration_guide.botted_library') as mock_lib:
                mock_lib.__version__ = "2.0.0"
                
                with patch('botted_library.migration.migration_guide.CollaborativeServer'):
                    readiness = check_migration_readiness()
                    
                    recommendations = readiness['recommendations']
                    assert any('ready' in rec.lower() for rec in recommendations)
                    assert any('test' in rec.lower() or 'run' in rec.lower() for rec in recommendations)
        
        # Test not ready state
        with patch('sys.version_info', (3, 6, 0)):  # Old Python
            readiness = check_migration_readiness()
            
            recommendations = readiness['recommendations']
            assert any('resolve' in rec.lower() or 'update' in rec.lower() for rec in recommendations)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_print_migration_readiness(self, mock_stdout):
        """Test printing readiness check results."""
        with patch('botted_library.migration.migration_guide.check_migration_readiness') as mock_check:
            mock_check.return_value = {
                'ready': True,
                'issues': [],
                'recommendations': ['Environment is ready', 'Run tests'],
                'python_version': '3.8.0',
                'botted_library_available': True,
                'botted_library_version': '2.0.0',
                'collaborative_server_available': True
            }
            
            print_migration_readiness()
            
            output = mock_stdout.getvalue()
            
            # Verify key information is printed
            assert "Readiness Check" in output
            assert "3.8.0" in output
            assert "ready" in output.lower()
            assert "✅" in output or "success" in output.lower()
            assert "Environment is ready" in output
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_print_migration_readiness_with_issues(self, mock_stdout):
        """Test printing readiness check with issues."""
        with patch('botted_library.migration.migration_guide.check_migration_readiness') as mock_check:
            mock_check.return_value = {
                'ready': False,
                'issues': ['Python version too old', 'Missing library'],
                'recommendations': ['Update Python', 'Install library'],
                'python_version': '3.6.0',
                'botted_library_available': False,
                'collaborative_server_available': False
            }
            
            print_migration_readiness()
            
            output = mock_stdout.getvalue()
            
            # Verify issues and recommendations are shown
            assert "Python version too old" in output
            assert "Missing library" in output
            assert "Update Python" in output
            assert "Install library" in output
            assert "❌" in output or "not" in output.lower()


class TestMigrationGuideIntegration:
    """Test integration aspects of the migration guide."""
    
    def test_guide_consistency(self):
        """Test that guide content is consistent and complete."""
        guide = get_migration_guide()
        
        # Verify all migration steps have unique step numbers
        steps = guide['migration_steps']
        step_numbers = [step['step'] for step in steps]
        assert len(step_numbers) == len(set(step_numbers))  # No duplicates
        assert step_numbers == list(range(1, len(steps) + 1))  # Sequential
        
        # Verify code examples are valid Python (basic check)
        for step in steps:
            code = step['code_example']
            assert 'from botted_library' in code or 'import' in code
            assert not code.startswith(' ')  # Should not start with whitespace
    
    def test_troubleshooting_completeness(self):
        """Test that troubleshooting covers common scenarios."""
        guide = get_migration_guide()
        issues = guide['troubleshooting']['common_issues']
        
        # Check for coverage of key problem areas
        issue_topics = [issue['issue'].lower() for issue in issues]
        
        expected_topics = ['collaborat', 'import', 'performance']
        for topic in expected_topics:
            assert any(topic in issue_topic for issue_topic in issue_topics), f"Missing coverage for {topic}"
    
    def test_feature_descriptions_quality(self):
        """Test that new feature descriptions are informative."""
        guide = get_migration_guide()
        features = guide['new_features']
        
        for feature_name, description in features.items():
            # Each description should be informative
            assert len(description) > 20  # Minimum length
            assert not description.endswith('.')  # Consistent formatting
            
            # Should describe what the feature does
            action_words = ['can', 'provide', 'enable', 'allow', 'support', 'manage']
            assert any(word in description.lower() for word in action_words)
    
    def test_best_practices_actionability(self):
        """Test that best practices are actionable."""
        guide = get_migration_guide()
        practices = guide['best_practices']
        
        for practice in practices:
            # Should be actionable (contain verbs)
            action_verbs = ['keep', 'use', 'test', 'monitor', 'start', 'introduce']
            assert any(verb in practice.lower() for verb in action_verbs), f"Practice not actionable: {practice}"
            
            # Should be specific enough
            assert len(practice) > 15  # Minimum specificity
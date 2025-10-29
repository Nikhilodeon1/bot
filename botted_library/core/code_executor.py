"""
Code Execution Engine for Botted Library

Provides basic code execution and validation capabilities.
"""

import os
import sys
import subprocess
import tempfile
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .exceptions import BottedLibraryError
from ..utils.logger import setup_logger


class CodeExecutionError(BottedLibraryError):
    """Code execution related errors"""
    pass


class CodeExecutor:
    """Basic code execution engine with security safeguards"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger(__name__)
        
        # Execution settings
        self.timeout = self.config.get('execution_timeout', 30)
        self.temp_dir = self.config.get('temp_directory', tempfile.gettempdir())
        
        self.logger.info("Code executor initialized")
    
    def execute_code(self, code: str, language: str = "python", 
                    inputs: List[str] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute code in a controlled environment"""
        try:
            self.logger.info(f"Executing {language} code")
            
            if language != "python":
                raise CodeExecutionError(f"Language {language} not supported in basic version")
            
            # Basic security validation
            self._validate_code_security(code)
            
            # Execute in temporary environment
            with tempfile.TemporaryDirectory(dir=self.temp_dir) as temp_dir:
                execution_result = self._execute_python_code(code, temp_dir, inputs)
            
            self.logger.info("Code execution completed")
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Code execution failed: {str(e)}")
            raise CodeExecutionError(f"Code execution failed: {str(e)}", original_exception=e)
    
    def test_code(self, code: str, test_cases: str, language: str = "python") -> Dict[str, Any]:
        """Execute code with test cases"""
        try:
            self.logger.info(f"Testing {language} code")
            
            if language != "python":
                raise CodeExecutionError(f"Language {language} not supported in basic version")
            
            # Combine code and tests
            full_code = code + "\n\n" + test_cases
            
            # Execute tests
            result = self.execute_code(full_code, language)
            
            # Parse test results
            test_result = {
                'success': result['success'],
                'output': result.get('stdout', ''),
                'errors': result.get('stderr', ''),
                'test_summary': {'passed': 1 if result['success'] else 0, 'failed': 0 if result['success'] else 1, 'total': 1},
                'language': language,
                'timestamp': datetime.now().isoformat()
            }
            
            return test_result
            
        except Exception as e:
            self.logger.error(f"Code testing failed: {str(e)}")
            raise CodeExecutionError(f"Code testing failed: {str(e)}", original_exception=e)
    
    def validate_syntax(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Validate code syntax without execution"""
        try:
            self.logger.debug(f"Validating {language} syntax")
            
            if language == "python":
                return self._validate_python_syntax(code)
            else:
                return {
                    'valid': True,
                    'errors': [],
                    'warnings': ['Syntax validation not implemented for this language']
                }
                
        except Exception as e:
            return {
                'valid': False,
                'errors': [str(e)],
                'warnings': []
            }
    
    def _validate_code_security(self, code: str) -> None:
        """Basic security validation"""
        
        # Check for dangerous operations
        dangerous_patterns = [
            'import os', 'import sys', 'import subprocess',
            'exec(', 'eval(', '__import__',
            'open(', 'file(', 'input(',
            'rm -rf', 'del ', 'format'
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                raise CodeExecutionError(f"Potentially dangerous operation detected: {pattern}")
    
    def _execute_python_code(self, code: str, temp_dir: str, inputs: List[str] = None) -> Dict[str, Any]:
        """Execute Python code safely"""
        
        # Create code file
        code_file = os.path.join(temp_dir, "main.py")
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Prepare input
        input_data = '\n'.join(inputs) if inputs else None
        
        # Execute with timeout
        try:
            result = subprocess.run(
                [sys.executable, code_file],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=temp_dir
            )
            
            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': 0.0,  # Simplified
                'language': 'python',
                'timestamp': datetime.now().isoformat()
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'return_code': -1,
                'stdout': '',
                'stderr': f'Execution timed out after {self.timeout} seconds',
                'execution_time': self.timeout,
                'language': 'python',
                'timestamp': datetime.now().isoformat()
            }
    
    def _validate_python_syntax(self, code: str) -> Dict[str, Any]:
        """Validate Python syntax"""
        import ast
        
        try:
            ast.parse(code)
            return {
                'valid': True,
                'errors': [],
                'warnings': []
            }
        except SyntaxError as e:
            return {
                'valid': False,
                'errors': [f"Syntax error at line {e.lineno}: {e.msg}"],
                'warnings': []
            }
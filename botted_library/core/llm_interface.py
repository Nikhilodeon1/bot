"""
LLM Interface for Botted Library

Provides integration with various LLM providers for intelligent decision making.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from .exceptions import BottedLibraryError
from ..utils.logger import setup_logger


class LLMError(BottedLibraryError):
    """LLM-related errors"""
    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def generate_structured_response(self, prompt: str, schema: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a structured response matching the given schema"""
        pass


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing and development"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = setup_logger(__name__)
    
    def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate mock response"""
        role = context.get('role', 'assistant') if context else 'assistant'
        
        # Generate contextual mock responses based on role and prompt
        if 'edit' in prompt.lower() or 'grammar' in prompt.lower():
            return "I have analyzed the text and made improvements to grammar, clarity, and style."
        elif 'research' in prompt.lower() or 'find' in prompt.lower():
            return "Based on my research from reliable sources, I have gathered comprehensive information on the requested topic."
        elif 'email' in prompt.lower() or 'categorize' in prompt.lower():
            return "I have processed and categorized the emails based on priority and content type."
        elif 'code' in prompt.lower() or 'program' in prompt.lower():
            return "I have analyzed the requirements and created a well-structured code solution."
        else:
            return f"As a {role}, I have processed your request and completed the task according to best practices."
    
    def generate_structured_response(self, prompt: str, schema: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate mock structured response"""
        mock_response = {}
        
        for key, value_type in schema.items():
            if key == 'reasoning':
                mock_response[key] = "I analyzed the task requirements and determined the optimal approach."
            elif key == 'plan' or key == 'steps':
                mock_response[key] = [
                    "Analyze the task requirements",
                    "Execute the task using appropriate methods",
                    "Validate results and ensure quality"
                ]
            elif key == 'confidence':
                mock_response[key] = 0.85
            elif key == 'result':
                mock_response[key] = "Task completed successfully."
            else:
                mock_response[key] = f"Mock value for {key}"
        
        return mock_response


class LLMInterface:
    """Main interface for LLM operations"""
    
    def __init__(self, provider: LLMProvider, config: Dict[str, Any] = None):
        self.provider = provider
        self.config = config or {}
        self.logger = setup_logger(__name__)
        
        # Conversation history for context
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_history = self.config.get('max_conversation_history', 10)
    
    def think(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate a thoughtful response to a prompt"""
        try:
            # Add conversation history to context
            full_context = context or {}
            if self.conversation_history:
                full_context['conversation_history'] = self.conversation_history[-5:]
            
            response = self.provider.generate_response(prompt, full_context)
            
            # Store in conversation history
            self._add_to_history(prompt, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLM thinking error: {str(e)}")
            raise LLMError(f"Failed to generate response: {str(e)}", original_exception=e)
    
    def generate_code(self, requirements: str, language: str = "python", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate code based on requirements"""
        try:
            code_prompt = f"""
            Requirements: {requirements}
            Language: {language}
            
            Please generate clean, well-documented code that meets these requirements.
            """
            
            schema = {
                'code': 'string',
                'explanation': 'string',
                'dependencies': 'array'
            }
            
            code_result = self.provider.generate_structured_response(code_prompt, schema, context)
            
            # Store code generation in history
            self._add_to_history(f"Generate code: {requirements}", "Code generated successfully")
            
            return code_result
            
        except Exception as e:
            self.logger.error(f"Code generation error: {str(e)}")
            raise LLMError(f"Failed to generate code: {str(e)}", original_exception=e)
    
    def _add_to_history(self, prompt: str, response: str) -> None:
        """Add exchange to conversation history"""
        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'response': response
        })
        
        # Maintain history size limit
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def clear_history(self) -> None:
        """Clear conversation history"""
        self.conversation_history.clear()


def create_llm_interface(provider_type: str = "gemini", **kwargs) -> LLMInterface:
    """Factory function to create LLM interface with specified provider"""
    
    if provider_type.lower() == "mock":
        provider = MockLLMProvider(kwargs.get('config', {}))
    else:
        raise LLMError(f"Provider type {provider_type} not implemented in simplified version")
    
    return LLMInterface(provider, kwargs.get('config', {}))
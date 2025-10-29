"""
LLM Interface for Botted Library
Supports multiple providers including Gemini 2.5 Flash
"""

import os
from typing import Dict, Any
import logging


class BaseLLM:
    """Base LLM interface"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def think(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate a response"""
        raise NotImplementedError
    
    def generate_code(self, requirements: str, language: str = "python", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate code"""
        raise NotImplementedError


class MockLLM(BaseLLM):
    """Mock LLM for testing and development"""
    
    def think(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate a mock response"""
        if 'plan' in prompt.lower():
            return """Here's a structured plan:
1. Research and analysis phase
2. Design and planning phase  
3. Implementation phase
4. Testing and validation phase
5. Review and optimization phase

Each phase includes specific deliverables and timelines."""
        
        elif 'code' in prompt.lower():
            return "I'll create a well-structured code solution that follows best practices and includes proper error handling."
        
        elif 'research' in prompt.lower():
            return "I'll gather comprehensive information from reliable sources and provide a detailed analysis of the findings."
        
        else:
            return "I have processed your request and provided an appropriate response based on my capabilities and the context provided."
    
    def generate_code(self, requirements: str, language: str = "python", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate mock code"""
        if language.lower() == "python":
            code = f'''# {requirements}
def main():
    """
    {requirements}
    """
    print("Hello, World!")
    return True

if __name__ == "__main__":
    main()'''
        else:
            code = f'// {requirements}\nconsole.log("Hello, World!");'
        
        return {
            'code': code,
            'explanation': f'Generated {language} code for: {requirements}',
            'dependencies': []
        }


class GeminiLLM(BaseLLM):
    """Google Gemini 2.5 Flash LLM implementation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('GEMINI_API_KEY')
        self.model = config.get('model', 'gemini-2.5-flash')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2048)
        
        if not self.api_key:
            raise ValueError("Gemini API key required. Set GEMINI_API_KEY environment variable or pass in config.")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            self.logger.info(f"Initialized Gemini {self.model}")
        except ImportError:
            raise ImportError("google-generativeai package required. Install with: pip install google-generativeai")
    
    def think(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response using Gemini"""
        try:
            # Add context if provided
            full_prompt = prompt
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items() if v])
                full_prompt = f"Context: {context_str}\n\nTask: {prompt}"
            
            response = self.client.generate_content(
                full_prompt,
                generation_config={
                    'temperature': self.temperature,
                    'max_output_tokens': self.max_tokens,
                }
            )
            
            return response.text.strip()
            
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            return f"I encountered an error processing your request: {str(e)}"
    
    def generate_code(self, requirements: str, language: str = "python", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate code using Gemini"""
        try:
            code_prompt = f"""Generate {language} code for the following requirements:
{requirements}

Please provide:
1. Clean, well-commented code
2. Proper error handling
3. Best practices for {language}

Return only the code without explanations."""

            response = self.client.generate_content(
                code_prompt,
                generation_config={
                    'temperature': 0.3,  # Lower temperature for code
                    'max_output_tokens': self.max_tokens,
                }
            )
            
            code = response.text.strip()
            
            # Clean up code formatting
            if code.startswith('```'):
                lines = code.split('\n')
                code = '\n'.join(lines[1:-1])  # Remove first and last lines
            
            return {
                'code': code,
                'explanation': f'Generated {language} code using Gemini 2.5 Flash',
                'dependencies': self._extract_dependencies(code, language)
            }
            
        except Exception as e:
            self.logger.error(f"Gemini code generation error: {e}")
            return {
                'code': f'# Error generating code: {str(e)}',
                'explanation': f'Code generation failed: {str(e)}',
                'dependencies': []
            }
    
    def _extract_dependencies(self, code: str, language: str) -> list:
        """Extract dependencies from generated code"""
        dependencies = []
        
        if language.lower() == 'python':
            lines = code.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Extract package name
                    if 'import ' in line:
                        pkg = line.split('import ')[1].split(' ')[0].split('.')[0]
                        if pkg not in ['os', 'sys', 'json', 'time', 'datetime']:  # Skip built-ins
                            dependencies.append(pkg)
        
        return list(set(dependencies))  # Remove duplicates


class OpenAILLM(BaseLLM):
    """OpenAI LLM implementation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        self.model = config.get('model', 'gpt-4')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2048)
        
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable or pass in config.")
        
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
            self.logger.info(f"Initialized OpenAI {self.model}")
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
    
    def think(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response using OpenAI"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items() if v])
                messages.insert(0, {"role": "system", "content": f"Context: {context_str}"})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return f"I encountered an error processing your request: {str(e)}"
    
    def generate_code(self, requirements: str, language: str = "python", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate code using OpenAI"""
        try:
            code_prompt = f"Generate {language} code for: {requirements}. Provide clean, well-commented code with proper error handling."
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": code_prompt}],
                temperature=0.3,
                max_tokens=self.max_tokens
            )
            
            code = response.choices[0].message.content.strip()
            
            # Clean up code formatting
            if code.startswith('```'):
                lines = code.split('\n')
                code = '\n'.join(lines[1:-1])
            
            return {
                'code': code,
                'explanation': f'Generated {language} code using OpenAI {self.model}',
                'dependencies': []
            }
            
        except Exception as e:
            self.logger.error(f"OpenAI code generation error: {e}")
            return {
                'code': f'# Error generating code: {str(e)}',
                'explanation': f'Code generation failed: {str(e)}',
                'dependencies': []
            }


def create_simple_llm(config: Dict[str, Any] = None) -> BaseLLM:
    """Create LLM instance based on configuration"""
    if not config:
        config = {}
    
    provider = config.get('provider', 'gemini').lower()
    
    if provider == 'gemini':
        return GeminiLLM(config)
    elif provider == 'openai':
        return OpenAILLM(config)
    elif provider == 'mock':
        return MockLLM(config)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Supported: gemini, openai, mock")
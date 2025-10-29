"""
Reasoning Engine for Botted Library

Provides basic reasoning and decision-making capabilities.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from .exceptions import BottedLibraryError
from ..utils.logger import setup_logger


class ReasoningError(BottedLibraryError):
    """Reasoning engine related errors"""
    pass


class ProblemType(Enum):
    """Types of problems the engine can solve"""
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    TECHNICAL = "technical"


class ReasoningEngine:
    """Basic reasoning engine for decision making and problem solving"""
    
    def __init__(self, llm_interface, config: Dict[str, Any] = None):
        self.llm = llm_interface
        self.config = config or {}
        self.logger = setup_logger(__name__)
        
        # Reasoning history for learning
        self.reasoning_history: List[Dict[str, Any]] = []
        
        self.logger.info("Reasoning engine initialized")
    
    def solve_problem(self, problem: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Solve a problem using reasoning"""
        try:
            self.logger.info("Solving problem with reasoning")
            
            # Use LLM to analyze and solve the problem
            solution_prompt = f"""
            Problem: {problem}
            
            Please analyze this problem and provide a solution with:
            1. Problem analysis
            2. Recommended solution
            3. Implementation steps
            4. Confidence level
            """
            
            schema = {
                'problem_analysis': 'string',
                'recommended_solution': 'string',
                'implementation_steps': 'array',
                'confidence': 'number'
            }
            
            solution = self.llm.provider.generate_structured_response(
                solution_prompt, schema, context
            )
            
            # Add reasoning metadata
            solution['timestamp'] = datetime.now().isoformat()
            
            # Store in reasoning history
            self._add_to_history('problem_solving', problem, solution)
            
            return solution
            
        except Exception as e:
            self.logger.error(f"Problem solving failed: {str(e)}")
            raise ReasoningError(f"Failed to solve problem: {str(e)}", original_exception=e)
    
    def make_decision(self, situation: str, options: List[str], 
                     criteria: List[str] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a decision using reasoning"""
        try:
            self.logger.info("Making decision")
            
            decision_prompt = f"""
            Situation: {situation}
            Options: {', '.join(options)}
            Criteria: {', '.join(criteria) if criteria else 'General best practices'}
            
            Please make the best decision and provide reasoning.
            """
            
            schema = {
                'chosen_option': 'string',
                'reasoning': 'string',
                'confidence': 'number'
            }
            
            decision = self.llm.provider.generate_structured_response(
                decision_prompt, schema, context
            )
            
            # Validate decision
            if decision['chosen_option'] not in options:
                decision['chosen_option'] = options[0]  # Default to first option
            
            decision['timestamp'] = datetime.now().isoformat()
            
            # Store in reasoning history
            self._add_to_history('decision_making', situation, decision)
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Decision making failed: {str(e)}")
            raise ReasoningError(f"Failed to make decision: {str(e)}", original_exception=e)
    
    def apply_common_sense(self, situation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply common sense reasoning to a situation"""
        try:
            self.logger.info("Applying common sense reasoning")
            
            common_sense_prompt = f"""
            Situation: {situation}
            
            Please apply common sense reasoning and provide:
            1. Reality check assessment
            2. Practical considerations
            3. Common sense recommendations
            """
            
            schema = {
                'reasonableness_assessment': 'string',
                'practical_constraints': 'array',
                'common_sense_recommendations': 'array',
                'confidence': 'number'
            }
            
            analysis = self.llm.provider.generate_structured_response(
                common_sense_prompt, schema, context
            )
            
            analysis['timestamp'] = datetime.now().isoformat()
            
            # Store in reasoning history
            self._add_to_history('common_sense_reasoning', situation, analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Common sense reasoning failed: {str(e)}")
            raise ReasoningError(f"Failed to apply common sense: {str(e)}", original_exception=e)
    
    def _add_to_history(self, reasoning_type: str, input_data: str, result: Dict[str, Any]) -> None:
        """Add reasoning to history for learning"""
        
        history_entry = {
            'reasoning_type': reasoning_type,
            'input': input_data,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        self.reasoning_history.append(history_entry)
        
        # Maintain history size
        max_history = self.config.get('max_reasoning_history', 100)
        if len(self.reasoning_history) > max_history:
            self.reasoning_history = self.reasoning_history[-max_history:]
    
    def get_reasoning_history(self) -> List[Dict[str, Any]]:
        """Get reasoning history"""
        return self.reasoning_history.copy()
    
    def clear_reasoning_history(self) -> None:
        """Clear reasoning history"""
        self.reasoning_history.clear()
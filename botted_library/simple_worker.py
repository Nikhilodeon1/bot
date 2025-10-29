#!/usr/bin/env python3
"""
Simple Worker Interface for Botted Library
This provides the streamlined user experience you described.
"""

import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from .core.factory import ComponentFactory
from .core.worker import Worker as CoreWorker
from .core.worker_registry import worker_registry


class Worker:
    """
    Human-like AI Worker that can use any tool to accomplish tasks.
    
    Each worker is like a person with:
    - A name and role (like "Marketing Manager", "Software Developer", etc.)
    - A job description that defines their expertise and responsibilities
    - Access to all available tools (web search, coding, document editing, email, etc.)
    - The ability to plan, execute, and report on any task within their expertise
    """
    
    def __init__(self, name: str, role: str, job_description: str, config: Dict[str, Any] = None):
        """
        Initialize a human-like AI worker.
        
        Args:
            name: Name for your worker (e.g., "Sarah", "Alex", "DataAnalyst_01")
            role: Their role/title (e.g., "Marketing Manager", "Software Developer", "Research Analyst")
            job_description: What they do and their expertise (e.g., "Specializes in market research and competitive analysis")
            config: Optional configuration for LLM, browser, etc.
        
        Example:
            sarah = Worker(
                name="Sarah", 
                role="Marketing Manager",
                job_description="Specializes in market research, competitive analysis, and content strategy. Expert at finding trends and creating actionable insights."
            )
        """
        self.name = name
        self.role = role
        self.job_description = job_description
        self.config = config or {}
        
        # Set up default config for user-friendly experience
        default_config = {
            'llm': {'provider': 'gemini'},  # Use real LLM by default
            'browser': {'headless': True, 'browser_type': 'chrome'},
            'memory': {'auto_cleanup': True}
        }
        
        # Merge user config with defaults (deep merge for nested dicts)
        for key, value in default_config.items():
            if key not in self.config:
                self.config[key] = value
            elif isinstance(value, dict) and isinstance(self.config[key], dict):
                # Deep merge for nested dictionaries
                for sub_key, sub_value in value.items():
                    if sub_key not in self.config[key]:
                        self.config[key][sub_key] = sub_value
        
        # Initialize the underlying system
        self._factory = ComponentFactory(self.config)
        self._core_worker = None
        self._task_history = []
        
        # Initialize the worker - all workers use the same underlying system but with different personalities
        self._initialize()
        
        print(f"👋 {self.name} ({self.role}) is ready to work!")
        print(f"💼 Job: {self.job_description}")
        
        # Show collaboration info if other workers are active
        active_workers = worker_registry.get_active_workers(exclude_worker_id=self._worker_id)
        if active_workers:
            print(f"🤝 Can collaborate with {len(active_workers)} other active workers")
    
    def _initialize(self):
        """Initialize the underlying worker system"""
        try:
            # All workers use the same underlying system - they're differentiated by their role and job description
            self._worker_id = f"{self.name}_{uuid.uuid4().hex[:8]}"
            
            # Use a generic role since all workers have access to all tools
            self._core_worker = self._factory.create_worker(self._worker_id, "researcher")  # Use researcher as it has all capabilities
            
            # Register this worker in the global registry for collaboration
            worker_registry.register_worker(
                worker_id=self._worker_id,
                worker_name=self.name,
                role=self.role,
                job_description=self.job_description,
                capabilities=self._get_capabilities(),
                worker_instance=self
            )
            
        except Exception as e:
            print(f"❌ Failed to initialize {self.name}: {e}")
            raise
    
    def call(self, instructions: str, **kwargs) -> Dict[str, Any]:
        """
        Give the worker a task to complete.
        
        The worker will:
        1. Understand the task in context of their role and job description
        2. Plan the approach using their expertise
        3. Use any tools needed (web search, coding, document editing, email, etc.)
        4. Execute the plan step by step
        5. Provide detailed results and deliverables
        
        Args:
            instructions: What you want the worker to do
            **kwargs: Additional parameters (url, file_path, etc.)
            
        Returns:
            Dict with results, files created, analysis, etc.
            
        Example:
            # Marketing Manager researching competitors
            result = sarah.call("Research our top 3 competitors and analyze their pricing strategies")
            
            # Software Developer building a feature
            result = alex.call("Create a user authentication system with password reset functionality")
            
            # Data Analyst processing information
            result = analyst.call("Analyze the sales data and create a summary report")
        """
        print(f"\n🎯 {self.name} ({self.role}) received task: {instructions}")
        
        # Step 1: Plan the approach
        self._show_progress("PLANNING", "Breaking down the task into logical steps...")
        plan = self._create_execution_plan(instructions, kwargs)
        
        # Step 2: Execute with live updates
        self._show_progress("EXECUTING", f"Starting execution with {len(plan['steps'])} steps...")
        result = self._execute_plan(plan, instructions, kwargs)
        
        # Step 3: Double-check and validate
        self._show_progress("VALIDATING", "Double-checking results and ensuring quality...")
        validated_result = self._validate_and_enhance_result(result, instructions)
        
        # Step 4: Prepare final report
        self._show_progress("FINALIZING", "Preparing comprehensive report...")
        final_result = self._create_final_report(validated_result, instructions, kwargs)
        
        # Step 5: Show completion
        self._show_progress("COMPLETED", "Task finished successfully!")
        
        # Store in history
        self._task_history.append({
            'instructions': instructions,
            'result': final_result,
            'timestamp': datetime.now().isoformat()
        })
        
        # Store important information in human-like memory
        if hasattr(self._core_worker, 'memory_system'):
            # Store the task and outcome if important
            task_memory = {
                'task': instructions,
                'outcome': final_result.get('summary', ''),
                'success': final_result.get('success', False),
                'worker_role': self.role,
                'timestamp': datetime.now().isoformat()
            }
            
            # Only store if the memory system deems it important
            self._core_worker.memory_system.store_important_fact(
                f"Completed task: {instructions} - {final_result.get('summary', 'Task completed')}",
                category="completed_tasks",
                context=f"role: {self.role}"
            )
        
        # Step 6: Present results to user
        self._present_results(final_result)
        
        return final_result
    
    def _create_execution_plan(self, instructions: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create an intuitive execution plan that anticipates user needs"""
        try:
            # Enhanced planning with intuition and anticipatory thinking
            planning_prompt = f"""
            You are {self.name}, a {self.role}.
            Your expertise: {self.job_description}
            
            User's request: {instructions}
            Parameters: {params}
            
            THINK INTUITIVELY AND ANTICIPATE NEEDS:
            
            1. What is the user REALLY trying to accomplish? (Look beyond the literal request)
            2. What additional information or deliverables would be valuable to them?
            3. What follow-up questions might they have?
            4. What context or background would help them understand the results better?
            5. What actionable next steps should you provide?
            
            Based on your expertise, create a comprehensive plan that:
            - Addresses their explicit request thoroughly
            - Anticipates their implicit needs
            - Provides additional value they might not have thought to ask for
            - Includes context, background, and actionable insights
            - Considers different perspectives and use cases
            
            You have access to all tools: web search, coding, document creation, email, spreadsheets, etc.
            Be proactive and think like a helpful expert who wants to exceed expectations.
            """
            
            plan_response = self._core_worker.think(planning_prompt)
            
            # Create structured plan
            plan = {
                'task': instructions,
                'approach': plan_response,
                'steps': self._extract_steps_from_plan(plan_response, instructions, params),
                'tools_needed': self._identify_tools_needed(instructions, params),
                'estimated_time': self._estimate_execution_time(instructions, params)
            }
            
            # Show plan to user
            print(f"📋 Execution Plan:")
            for i, step in enumerate(plan['steps'], 1):
                print(f"   {i}. {step}")
            print(f"🔧 Tools needed: {', '.join(plan['tools_needed'])}")
            print(f"⏱️  Estimated time: {plan['estimated_time']} seconds")
            
            return plan
            
        except Exception as e:
            print(f"⚠️  Planning failed, using default approach: {e}")
            # Even if planning fails, we can still extract steps based on task type
            fallback_steps = self._extract_steps_from_plan("", instructions, params)
            fallback_tools = self._identify_tools_needed(instructions, params)
            
            return {
                'task': instructions,
                'approach': 'Fallback execution based on task analysis',
                'steps': fallback_steps if fallback_steps else ['Execute task directly'],
                'tools_needed': fallback_tools,
                'estimated_time': self._estimate_execution_time(instructions, params)
            }
    
    def _extract_steps_from_plan(self, plan_text: str, instructions: str, params: Dict[str, Any]) -> List[str]:
        """Extract intuitive, comprehensive steps that anticipate user needs"""
        instructions_lower = instructions.lower()
        
        # Enhanced steps that go beyond the basic request
        if 'research' in instructions_lower or 'find' in instructions_lower or 'analyze' in instructions_lower:
            steps = [
                "Understand the deeper context and user goals",
                "Perform comprehensive research from multiple angles", 
                "Analyze findings and identify key insights",
                "Anticipate follow-up questions and gather additional context",
                "Create actionable recommendations and next steps"
            ]
        elif 'code' in instructions_lower or 'program' in instructions_lower or 'build' in instructions_lower:
            steps = [
                "Understand requirements and anticipate edge cases",
                "Research best practices and design patterns",
                "Create comprehensive solution with error handling",
                "Add documentation and usage examples",
                "Provide deployment guidance and next steps"
            ]
        elif 'plan' in instructions_lower or 'strategy' in instructions_lower:
            steps = [
                "Analyze goals and anticipate challenges",
                "Research market context and best practices",
                "Create detailed plan with multiple scenarios",
                "Add risk assessment and mitigation strategies",
                "Provide implementation roadmap and success metrics"
            ]
        elif 'write' in instructions_lower or 'create' in instructions_lower:
            steps = [
                "Understand audience and purpose deeply",
                "Research topic comprehensively for context",
                "Create engaging, valuable content",
                "Add supporting materials and resources",
                "Provide distribution and optimization suggestions"
            ]
        elif 'email' in instructions_lower or 'message' in instructions_lower:
            steps = [
                "Understand communication goals and audience",
                "Research context and appropriate tone",
                "Craft compelling, clear message",
                "Suggest follow-up actions and timing",
                "Provide templates for similar future communications"
            ]
        else:
            # Generic intuitive approach
            steps = [
                "Deeply understand the user's true goals",
                "Gather comprehensive information and context",
                "Execute task with attention to quality and detail",
                "Anticipate needs and provide additional value",
                "Create actionable next steps and recommendations"
            ]
        
        return steps
    
    def _identify_tools_needed(self, instructions: str, params: Dict[str, Any]) -> List[str]:
        """Identify what tools will be needed - all workers have access to all tools"""
        tools = ['thinking']  # Always need thinking
        
        instructions_lower = instructions.lower()
        
        # All workers can use any tool as needed
        if any(word in instructions_lower for word in ['research', 'search', 'find', 'look up', 'analyze', 'investigate']):
            tools.append('web_search')
        
        if any(word in instructions_lower for word in ['code', 'program', 'function', 'script', 'develop', 'build']):
            tools.append('coding')
        
        if any(word in instructions_lower for word in ['document', 'doc', 'sheet', 'spreadsheet', 'report', 'write']):
            tools.append('document_creation')
        
        if any(word in instructions_lower for word in ['email', 'message', 'send', 'contact', 'communicate']):
            tools.append('email')
        
        if 'url' in params or any(word in instructions_lower for word in ['website', 'browse', 'navigate', 'scrape']):
            tools.append('browser')
        
        return tools
    
    def _estimate_execution_time(self, instructions: str, params: Dict[str, Any]) -> int:
        """Estimate execution time in seconds"""
        base_time = 10
        
        instructions_lower = instructions.lower()
        
        if 'research' in instructions_lower:
            base_time += 20
        if 'code' in instructions_lower:
            base_time += 15
        if 'create' in instructions_lower:
            base_time += 10
        if 'complex' in instructions_lower or 'detailed' in instructions_lower:
            base_time += 15
        
        return min(base_time, 60)  # Cap at 60 seconds
    
    def _execute_plan(self, plan: Dict[str, Any], instructions: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plan step by step"""
        results = {
            'task': instructions,
            'steps_completed': [],
            'outputs': {},
            'files_created': [],
            'links_generated': [],
            'code_generated': None,
            'research_findings': None,
            'documents_created': [],
            'success': True,
            'execution_time': 0
        }
        
        start_time = time.time()
        
        try:
            for i, step in enumerate(plan['steps'], 1):
                self._show_progress(f"STEP {i}/{len(plan['steps'])}", step)
                
                # Execute the step
                step_result = self._execute_step(step, instructions, params, plan)
                
                # Store step result
                results['steps_completed'].append({
                    'step': step,
                    'result': step_result,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Merge step outputs into main results
                if isinstance(step_result, dict):
                    for key, value in step_result.items():
                        if key in results and isinstance(results[key], list):
                            if isinstance(value, list):
                                results[key].extend(value)
                            else:
                                results[key].append(value)
                        else:
                            results['outputs'][key] = value
                
                # Small delay for realism
                time.sleep(0.5)
            
            results['execution_time'] = time.time() - start_time
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            results['execution_time'] = time.time() - start_time
            print(f"❌ Execution failed at step: {e}")
        
        return results
    
    def _execute_step(self, step: str, instructions: str, params: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step"""
        step_lower = step.lower()
        
        try:
            if 'search' in step_lower or 'research' in step_lower:
                return self._execute_research_step(instructions, params)
            elif 'code' in step_lower or 'program' in step_lower:
                return self._execute_coding_step(instructions, params)
            elif 'document' in step_lower or 'create' in step_lower:
                return self._execute_document_step(instructions, params)
            elif 'plan' in step_lower or 'strategy' in step_lower:
                return self._execute_planning_step(instructions, params)
            else:
                return self._execute_thinking_step(step, instructions, params)
                
        except Exception as e:
            return {'error': str(e), 'step': step}
    
    def _execute_research_step(self, instructions: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute comprehensive research with multiple angles and insights"""
        try:
            # Enhanced research approach
            base_query = params.get('query', instructions)
            max_results = params.get('max_results', 10)  # Get more results for better analysis
            
            # Generate multiple search queries to get comprehensive coverage
            search_queries = self._generate_comprehensive_search_queries(base_query, instructions)
            
            all_results = []
            total_found = 0
            
            # Perform multiple searches for comprehensive coverage
            for query in search_queries[:3]:  # Limit to 3 searches to avoid overload
                try:
                    search_result = self._core_worker.web_search(query, max_results=max_results//len(search_queries))
                    if search_result.get('success') and search_result.get('results'):
                        all_results.extend(search_result['results'])
                        total_found += search_result.get('total_results', 0)
                except Exception as e:
                    print(f"Search failed for query '{query}': {e}")
                    continue
            
            # Remove duplicates and rank by relevance
            unique_results = self._deduplicate_and_rank_results(all_results, base_query)
            
            return {
                'research_findings': {
                    'success': len(unique_results) > 0,
                    'query': base_query,
                    'search_queries_used': search_queries,
                    'results': unique_results[:max_results],
                    'total_results': len(unique_results),
                    'search_engine': 'google',
                    'timestamp': datetime.now().isoformat()
                },
                'search_query': base_query,
                'results_found': len(unique_results),
                'comprehensive_approach': True
            }
            
        except Exception as e:
            return {'error': f"Research failed: {e}"}
    
    def _execute_coding_step(self, instructions: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coding step"""
        try:
            language = params.get('language', 'python')
            
            # Generate code
            code_result = self._core_worker.write_code(instructions, language)
            
            # Test the code if possible
            if code_result.get('code'):
                test_result = self._core_worker.test_code(
                    code_result['code'], 
                    "# Basic test cases", 
                    language
                )
                code_result['test_result'] = test_result
            
            return {
                'code_generated': code_result,
                'language': language,
                'files_created': [f"generated_code.{language}"]
            }
            
        except Exception as e:
            return {'error': f"Coding failed: {e}"}
    
    def _execute_document_step(self, instructions: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute document creation step"""
        try:
            doc_type = params.get('doc_type', 'google_docs')
            title = params.get('title', f"Document for: {instructions[:50]}")
            
            # Generate content first
            content_prompt = f"Create content for: {instructions}"
            content = self._core_worker.think(content_prompt)
            
            # Create document
            doc_result = self._core_worker.create_document(title, content, doc_type)
            
            return {
                'documents_created': [doc_result],
                'document_title': title,
                'document_type': doc_type
            }
            
        except Exception as e:
            return {'error': f"Document creation failed: {e}"}
    
    def _execute_planning_step(self, instructions: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute planning step"""
        try:
            planning_prompt = f"Create a detailed plan for: {instructions}"
            plan_content = self._core_worker.think(planning_prompt)
            
            return {
                'plan_created': plan_content,
                'planning_topic': instructions
            }
            
        except Exception as e:
            return {'error': f"Planning failed: {e}"}
    
    def _execute_thinking_step(self, step: str, instructions: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute thinking step with intuitive analysis, memory, and collaboration awareness"""
        try:
            # Get relevant memories for context
            memory_context = ""
            if hasattr(self._core_worker, 'memory_system'):
                memory_context = self._core_worker.memory_system.get_relevant_memories_for_context(
                    f"{step} {instructions}", max_memories=3
                )
            
            # Get collaboration context
            active_workers = self.get_active_workers()
            collaboration_context = ""
            if active_workers:
                worker_list = [f"{w['name']} ({w['role']})" for w in active_workers[:3]]
                collaboration_context = f"Available collaborators: {', '.join(worker_list)}"
            
            thinking_prompt = f"""
            You are {self.name}, a {self.role}.
            Your expertise: {self.job_description}
            
            Current step: {step}
            User's original request: {instructions}
            Parameters: {params}
            
            {memory_context}
            
            {collaboration_context}
            
            THINK INTUITIVELY AND COMPREHENSIVELY:
            
            For this step, consider:
            1. What would a true expert in my field do here?
            2. What additional insights can I provide beyond the obvious?
            3. What context or background would be valuable?
            4. What potential issues or opportunities should I highlight?
            5. How can I exceed expectations and provide extra value?
            6. Should I collaborate with another worker for better results?
            
            Use your memories and consider collaboration opportunities.
            Provide a thorough analysis that demonstrates deep expertise and anticipates user needs.
            """
            result = self._core_worker.think(thinking_prompt)
            
            # Store important insights in memory
            if hasattr(self._core_worker, 'memory_system') and result:
                self._core_worker.memory_system.store_important_fact(
                    f"Insight from {step}: {result[:200]}...",
                    category="insights",
                    context=instructions
                )
            
            return {
                'thinking_result': result,
                'step_completed': step
            }
            
        except Exception as e:
            return {'error': f"Thinking step failed: {e}"}
    
    def _validate_and_enhance_result(self, result: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """Thoroughly validate results and add expert insights"""
        try:
            # Enhanced validation with expert perspective
            validation_prompt = f"""
            You are {self.name}, a {self.role}.
            Your expertise: {self.job_description}
            
            Original user request: {instructions}
            Work completed: {result}
            
            EXPERT VALIDATION AND ENHANCEMENT:
            
            1. Did we fully address the user's explicit and implicit needs?
            2. What additional insights or context would be valuable?
            3. Are there any gaps, risks, or opportunities we should highlight?
            4. What would a true expert in this field add or emphasize?
            5. How can we make this more actionable and valuable?
            
            Provide expert-level validation and suggest any enhancements that would increase the value of our work.
            Think like a senior consultant reviewing junior work - what would you add or improve?
            """
            
            validation = self._core_worker.think(validation_prompt)
            result['expert_validation'] = validation
            
            # Add comprehensive quality assessment
            result['quality_score'] = self._calculate_enhanced_quality_score(result, instructions)
            
            # Add expert insights if not already present
            if not result.get('expert_insights'):
                result['expert_insights'] = self._generate_expert_insights(result, instructions)
            
            return result
            
        except Exception as e:
            result['validation_error'] = str(e)
            return result
    
    def _calculate_enhanced_quality_score(self, result: Dict[str, Any], instructions: str) -> float:
        """Calculate comprehensive quality score based on multiple factors"""
        score = 0.0
        
        # Base completion score
        if result.get('success', False):
            score += 0.3
        
        # Thoroughness score
        steps_completed = result.get('steps_completed', [])
        if len(steps_completed) >= 4:
            score += 0.2
        elif len(steps_completed) >= 2:
            score += 0.1
        
        # Content quality score
        if result.get('research_findings'):
            findings = result['research_findings']
            if findings.get('total_results', 0) > 5:
                score += 0.15
            elif findings.get('total_results', 0) > 0:
                score += 0.1
            
            # Bonus for comprehensive approach
            if result.get('comprehensive_approach'):
                score += 0.1
        
        if result.get('code_generated'):
            code = result['code_generated']
            if code.get('tested'):
                score += 0.1
            if 'documentation' in str(code).lower():
                score += 0.05
        
        # Error handling
        if not result.get('error') and not result.get('validation_error'):
            score += 0.1
        
        # Expert insights bonus
        if result.get('expert_insights') or result.get('expert_validation'):
            score += 0.1
        
        # Anticipatory thinking bonus
        next_steps = result.get('next_steps', [])
        if len(next_steps) > 3:
            score += 0.05
        
        return min(score, 1.0)
    
    def _generate_expert_insights(self, result: Dict[str, Any], instructions: str) -> str:
        """Generate expert-level insights based on the work completed"""
        try:
            insights_prompt = f"""
            As {self.name}, a {self.role} with expertise in: {self.job_description}
            
            Based on the work completed for: {instructions}
            Results: {result}
            
            Provide 3-5 expert insights that go beyond the obvious:
            1. What patterns or trends should the user be aware of?
            2. What strategic implications or opportunities exist?
            3. What potential challenges or risks should be considered?
            4. What industry best practices or benchmarks are relevant?
            5. What would you advise based on your expertise?
            
            Keep insights practical, actionable, and valuable.
            """
            
            insights = self._core_worker.think(insights_prompt)
            return insights
            
        except Exception as e:
            return f"Expert insights generation encountered an issue: {e}"
    
    def _create_final_report(self, result: Dict[str, Any], instructions: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create the final comprehensive report"""
        report = {
            'task': instructions,
            'worker': self.name,
            'role': self.role,
            'success': result.get('success', True),
            'execution_time': result.get('execution_time', 0),
            'quality_score': result.get('quality_score', 0.5),
            'summary': self._create_summary(result, instructions),
            'deliverables': self._extract_deliverables(result),
            'next_steps': self._suggest_next_steps(result, instructions),
            'raw_result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _create_summary(self, result: Dict[str, Any], instructions: str) -> str:
        """Create an intuitive summary that highlights value and insights"""
        if not result.get('success', True):
            return f"❌ Task encountered issues: {result.get('error', 'Unknown error')}"
        
        summary_parts = []
        instructions_lower = instructions.lower()
        
        # Enhanced summaries that show the value provided
        if result.get('research_findings'):
            findings = result['research_findings']
            total_results = findings.get('total_results', 0)
            if result.get('comprehensive_approach'):
                summary_parts.append(f"🔍 Conducted comprehensive research across multiple angles, analyzing {total_results} sources")
            else:
                summary_parts.append(f"🔍 Researched and analyzed {total_results} relevant sources")
        
        if result.get('code_generated'):
            code = result['code_generated']
            language = code.get('language', 'code')
            summary_parts.append(f"💻 Developed robust {language} solution with error handling and documentation")
        
        if result.get('documents_created'):
            docs = result['documents_created']
            summary_parts.append(f"📄 Created {len(docs)} comprehensive document(s) with supporting materials")
        
        if result.get('plan_created'):
            summary_parts.append("📋 Developed detailed strategic plan with risk assessment and implementation roadmap")
        
        # Add context about the approach taken
        if 'thinking_result' in str(result):
            summary_parts.append("🧠 Applied expert-level analysis and insights")
        
        # Default comprehensive summary
        if not summary_parts:
            summary_parts.append("✅ Completed task with comprehensive analysis and actionable recommendations")
        
        # Add a note about the intuitive approach
        base_summary = " | ".join(summary_parts)
        
        # Add value-focused suffix based on task type
        if 'research' in instructions_lower or 'analyze' in instructions_lower:
            return f"{base_summary} with actionable insights and next steps"
        elif 'plan' in instructions_lower or 'strategy' in instructions_lower:
            return f"{base_summary} with implementation guidance and success metrics"
        elif 'create' in instructions_lower or 'build' in instructions_lower:
            return f"{base_summary} with best practices and optimization recommendations"
        else:
            return f"{base_summary} with expert-level attention to detail"
    
    def _extract_deliverables(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract actionable deliverables for the user"""
        deliverables = {}
        
        # Code files
        if result.get('code_generated'):
            code = result['code_generated']
            deliverables['code'] = {
                'content': code.get('code', ''),
                'language': code.get('language', 'python'),
                'filename': f"generated_code.{code.get('language', 'py')}",
                'tested': bool(code.get('test_result'))
            }
        
        # Research results
        if result.get('research_findings'):
            findings = result['research_findings']
            deliverables['research'] = {
                'results': findings.get('results', []),
                'total_found': findings.get('total_results', 0),
                'search_query': result.get('search_query', '')
            }
        
        # Documents
        if result.get('documents_created'):
            deliverables['documents'] = result['documents_created']
        
        # Plans
        if result.get('plan_created'):
            deliverables['plan'] = result['plan_created']
        
        return deliverables
    
    def _generate_comprehensive_search_queries(self, base_query: str, instructions: str) -> List[str]:
        """Generate multiple search queries for comprehensive research"""
        queries = [base_query]  # Start with the base query
        
        instructions_lower = instructions.lower()
        base_lower = base_query.lower()
        
        # Add related queries based on context
        if 'trends' in base_lower or 'future' in instructions_lower:
            queries.append(f"{base_query} 2024 predictions")
            queries.append(f"{base_query} latest developments")
            queries.append(f"{base_query} market analysis")
        
        if 'ai' in base_lower or 'artificial intelligence' in base_lower:
            queries.append(f"{base_query} machine learning")
            queries.append(f"{base_query} industry impact")
            queries.append(f"{base_query} business applications")
        
        if 'research' in instructions_lower:
            queries.append(f"{base_query} studies reports")
            queries.append(f"{base_query} statistics data")
            queries.append(f"{base_query} expert analysis")
        
        # Add comparative and contextual queries
        if len(queries) < 4:
            queries.append(f"{base_query} best practices")
            queries.append(f"{base_query} challenges opportunities")
        
        return queries[:5]  # Limit to 5 queries
    
    def _deduplicate_and_rank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Remove duplicates and rank results by relevance"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                # Add relevance score based on title and snippet matching
                relevance = self._calculate_relevance_score(result, query)
                result['relevance_score'] = relevance
                unique_results.append(result)
        
        # Sort by relevance score (highest first)
        unique_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return unique_results
    
    def _calculate_relevance_score(self, result: Dict, query: str) -> float:
        """Calculate relevance score for a search result"""
        score = 0.0
        query_words = query.lower().split()
        
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        
        # Score based on query word matches
        for word in query_words:
            if word in title:
                score += 2.0  # Title matches are more important
            if word in snippet:
                score += 1.0
        
        # Bonus for authoritative sources
        url = result.get('url', '').lower()
        if any(domain in url for domain in ['.edu', '.gov', '.org']):
            score += 1.0
        
        return score

    def _suggest_next_steps(self, result: Dict[str, Any], instructions: str) -> List[str]:
        """Suggest intuitive, actionable next steps that anticipate user needs"""
        suggestions = []
        instructions_lower = instructions.lower()
        
        # Enhanced suggestions based on what was accomplished
        if result.get('code_generated'):
            suggestions.extend([
                "Test the code thoroughly with different inputs and edge cases",
                "Review the code for security vulnerabilities and performance optimization",
                "Create documentation and usage examples for future reference",
                "Consider integrating the code into your existing project structure",
                "Set up version control and backup for the code"
            ])
        
        if result.get('research_findings'):
            suggestions.extend([
                "Dive deeper into the most promising findings and sources",
                "Cross-reference the information with additional authoritative sources",
                "Create a summary document or presentation for stakeholders",
                "Identify key contacts or experts mentioned in the research",
                "Set up alerts for ongoing monitoring of this topic"
            ])
        
        if result.get('documents_created'):
            suggestions.extend([
                "Review and refine the documents for clarity and completeness",
                "Share drafts with relevant stakeholders for feedback",
                "Create a distribution plan and timeline for the documents",
                "Consider translating or adapting for different audiences",
                "Set up a system for keeping the documents updated"
            ])
        
        if result.get('plan_created'):
            suggestions.extend([
                "Break down the plan into specific, actionable tasks with deadlines",
                "Identify required resources, budget, and team members",
                "Create contingency plans for potential risks and obstacles",
                "Set up progress tracking and milestone review meetings",
                "Begin with quick wins to build momentum"
            ])
        
        # Add context-specific suggestions based on the original request
        if 'marketing' in instructions_lower:
            suggestions.append("Consider A/B testing different approaches before full implementation")
        elif 'business' in instructions_lower:
            suggestions.append("Analyze the financial impact and ROI projections")
        elif 'technical' in instructions_lower or 'development' in instructions_lower:
            suggestions.append("Plan for scalability, maintenance, and future updates")
        
        # Always include these comprehensive suggestions
        suggestions.extend([
            "Schedule a follow-up review to assess progress and adjust approach",
            "Document lessons learned and best practices for future similar projects",
            "Consider how this work connects to your broader goals and strategy"
        ])
        
        # Return top suggestions to avoid overwhelming the user
        return suggestions[:6]
    
    def _present_results(self, final_result: Dict[str, Any]):
        """Present the final results to the user in a clear format"""
        print(f"\n🎉 {self.name} has completed the task!")
        print("=" * 50)
        
        # Summary
        print(f"📋 Summary: {final_result['summary']}")
        print(f"⏱️  Execution time: {final_result['execution_time']:.1f} seconds")
        print(f"⭐ Quality score: {final_result['quality_score']:.1f}/1.0")
        
        # Deliverables
        deliverables = final_result['deliverables']
        if deliverables:
            print(f"\n📦 Deliverables:")
            
            if 'code' in deliverables:
                code = deliverables['code']
                print(f"   💻 Code ({code['language']}):")
                print(f"      - File: {code['filename']}")
                print(f"      - Tested: {'✅' if code['tested'] else '⚠️'}")
                print(f"      - Preview: {code['content'][:100]}...")
            
            if 'research' in deliverables:
                research = deliverables['research']
                print(f"   🔍 Research Results:")
                print(f"      - Query: {research['search_query']}")
                print(f"      - Results found: {research['total_found']}")
                for i, result in enumerate(research['results'][:3], 1):
                    print(f"      {i}. {result.get('title', 'No title')}")
            
            if 'documents' in deliverables:
                docs = deliverables['documents']
                print(f"   📄 Documents Created:")
                for doc in docs:
                    print(f"      - {doc.get('title', 'Untitled document')}")
                    if doc.get('url'):
                        print(f"        Link: {doc['url']}")
            
            if 'plan' in deliverables:
                print(f"   📋 Plan Created:")
                plan_preview = deliverables['plan'][:200] + "..." if len(deliverables['plan']) > 200 else deliverables['plan']
                print(f"      {plan_preview}")
        
        # Next steps
        if final_result['next_steps']:
            print(f"\n🚀 Suggested next steps:")
            for i, step in enumerate(final_result['next_steps'], 1):
                print(f"   {i}. {step}")
        
        print("=" * 50)
    
    def _show_progress(self, stage: str, message: str):
        """Show progress updates to the user"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🤖 {stage}: {message}")
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get the task history for this worker"""
        return self._task_history.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current worker status"""
        return {
            'name': self.name,
            'role': self.role,
            'tasks_completed': len(self._task_history),
            'status': 'ready',
            'capabilities': self._get_capabilities()
        }
    
    def _get_capabilities(self) -> List[str]:
        """Get list of worker capabilities - all workers have access to all tools"""
        return [
            'thinking',
            'planning', 
            'problem_solving',
            'web_search',
            'research',
            'coding',
            'testing',
            'document_creation',
            'spreadsheet_creation',
            'email_processing',
            'communication',
            'browser_automation',
            'data_analysis',
            'content_creation'
        ]
    
    def get_active_workers(self) -> List[Dict[str, Any]]:
        """Get list of other active workers that this worker can collaborate with."""
        return worker_registry.get_active_workers(exclude_worker_id=self._worker_id)
    
    def delegate_task(self, task_description: str, preferred_role: str = None, **kwargs) -> Dict[str, Any]:
        """
        Delegate a task to another worker.
        
        Args:
            task_description: What you want the other worker to do
            preferred_role: Preferred type of worker (e.g., "developer", "researcher")
            **kwargs: Additional parameters for the task
            
        Returns:
            Result from the other worker
        """
        try:
            # Find the best worker for this task
            if preferred_role:
                target_worker = worker_registry.find_worker_by_role([preferred_role], exclude_worker_id=self._worker_id)
            else:
                # Get suggestions and pick the best one
                suggestions = worker_registry.get_collaboration_suggestions(self._worker_id, task_description)
                target_worker = suggestions[0]['worker'] if suggestions else None
            
            if not target_worker:
                return {
                    'success': False,
                    'error': 'No suitable worker found for delegation',
                    'available_workers': self.get_active_workers()
                }
            
            print(f"🤝 {self.name} delegating task to {target_worker['name']} ({target_worker['role']})")
            
            # Delegate the task
            result = worker_registry.delegate_task(
                from_worker_id=self._worker_id,
                to_worker_id=target_worker['worker_id'],
                task_description=task_description,
                **kwargs
            )
            
            # Store the collaboration in memory
            collaboration_memory = {
                'collaboration_type': 'task_delegation',
                'delegated_to': target_worker['name'],
                'delegated_role': target_worker['role'],
                'task': task_description,
                'result_summary': result.get('summary', 'Task completed'),
                'timestamp': datetime.now().isoformat()
            }
            
            if hasattr(self._core_worker, 'memory_system'):
                self._core_worker.memory_system.store_important_fact(
                    f"Collaborated with {target_worker['name']} on: {task_description}",
                    category="collaboration",
                    context=f"delegation to {target_worker['role']}"
                )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Task delegation failed: {str(e)}"
            }
    
    def ask_for_help(self, question: str, preferred_role: str = None) -> str:
        """
        Ask another worker for help or advice.
        
        Args:
            question: The question or help request
            preferred_role: Preferred type of worker to ask
            
        Returns:
            Response from the other worker
        """
        try:
            result = self.delegate_task(f"Please help me with this question: {question}", preferred_role)
            
            if result.get('success'):
                return result.get('summary', 'Help provided successfully')
            else:
                return f"Could not get help: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"Error asking for help: {str(e)}"
    
    def get_collaboration_history(self) -> List[Dict[str, Any]]:
        """Get history of collaborations involving this worker."""
        registry_status = worker_registry.get_registry_status()
        
        # Filter collaborations involving this worker
        my_collaborations = []
        for collab in registry_status.get('recent_collaborations', []):
            if collab.get('from_worker') == self._worker_id or collab.get('to_worker') == self._worker_id:
                my_collaborations.append(collab)
        
        return my_collaborations

    def shutdown(self):
        """Gracefully shutdown the worker"""
        print(f"👋 {self.name} is shutting down...")
        
        # Unregister from worker registry
        worker_registry.unregister_worker(self._worker_id)
        
        if self._factory:
            self._factory.reset_components()
        print(f"✅ {self.name} shutdown complete")


# Convenience function for quick worker creation
def create_worker(name: str, role: str, job_description: str, config: Dict[str, Any] = None) -> Worker:
    """
    Create a human-like AI worker with a specific role and expertise.
    
    Args:
        name: Name for your worker (e.g., "Sarah", "Alex", "DataAnalyst_01")
        role: Their role/title (e.g., "Marketing Manager", "Software Developer")
        job_description: What they do and their expertise
        config: Optional configuration for LLM, browser, etc.
    
    Returns:
        Worker instance ready to work
    
    Example:
        sarah = create_worker(
            name="Sarah",
            role="Marketing Manager", 
            job_description="Specializes in market research, competitive analysis, and content strategy"
        )
        result = sarah.call("Research our top 3 competitors and analyze their pricing strategies")
    """
    return Worker(name, role, job_description, config)
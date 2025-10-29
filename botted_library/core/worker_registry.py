"""
Worker Registry for Collaboration

Manages active workers and enables collaboration between them.
Workers can discover each other and delegate tasks for teamwork.
"""

import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
from .exceptions import WorkerError


class WorkerRegistry:
    """
    Global registry for managing active workers and enabling collaboration.
    
    This singleton class tracks all active workers in the current process
    and provides methods for workers to discover and collaborate with each other.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(WorkerRegistry, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self.active_workers: Dict[str, Dict[str, Any]] = {}
            self.collaboration_history: List[Dict[str, Any]] = []
            self._lock = threading.Lock()
            self._initialized = True
    
    def register_worker(self, worker_id: str, worker_name: str, role: str, 
                       job_description: str, capabilities: List[str], 
                       worker_instance=None) -> None:
        """
        Register a new active worker.
        
        Args:
            worker_id: Unique identifier for the worker
            worker_name: Human-readable name of the worker
            role: Worker's role/title
            job_description: Description of worker's expertise
            capabilities: List of worker's capabilities
            worker_instance: Reference to the actual worker instance
        """
        with self._lock:
            self.active_workers[worker_id] = {
                'worker_id': worker_id,
                'name': worker_name,
                'role': role,
                'job_description': job_description,
                'capabilities': capabilities,
                'registered_at': datetime.now().isoformat(),
                'status': 'active',
                'current_task': None,
                'worker_instance': worker_instance,
                'tasks_completed': 0,
                'collaboration_count': 0
            }
    
    def unregister_worker(self, worker_id: str) -> None:
        """Remove a worker from the active registry."""
        with self._lock:
            if worker_id in self.active_workers:
                del self.active_workers[worker_id]
    
    def get_active_workers(self, exclude_worker_id: str = None) -> List[Dict[str, Any]]:
        """
        Get list of all active workers, optionally excluding one worker.
        
        Args:
            exclude_worker_id: Worker ID to exclude from the list
            
        Returns:
            List of active worker information (without worker instances)
        """
        with self._lock:
            workers = []
            for worker_id, worker_info in self.active_workers.items():
                if exclude_worker_id and worker_id == exclude_worker_id:
                    continue
                
                # Return worker info without the instance reference
                worker_data = {k: v for k, v in worker_info.items() if k != 'worker_instance'}
                workers.append(worker_data)
            
            return workers
    
    def find_worker_by_capability(self, capability: str, exclude_worker_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Find a worker with a specific capability.
        
        Args:
            capability: The capability to search for
            exclude_worker_id: Worker ID to exclude from search
            
        Returns:
            Worker information if found, None otherwise
        """
        with self._lock:
            for worker_id, worker_info in self.active_workers.items():
                if exclude_worker_id and worker_id == exclude_worker_id:
                    continue
                
                if capability in worker_info.get('capabilities', []):
                    return {k: v for k, v in worker_info.items() if k != 'worker_instance'}
            
            return None
    
    def find_worker_by_role(self, role_keywords: List[str], exclude_worker_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Find a worker whose role matches the given keywords.
        
        Args:
            role_keywords: Keywords to search for in worker roles
            exclude_worker_id: Worker ID to exclude from search
            
        Returns:
            Worker information if found, None otherwise
        """
        with self._lock:
            for worker_id, worker_info in self.active_workers.items():
                if exclude_worker_id and worker_id == exclude_worker_id:
                    continue
                
                role = worker_info.get('role', '').lower()
                job_desc = worker_info.get('job_description', '').lower()
                
                # Check if any keyword matches the role or job description
                if any(keyword.lower() in role or keyword.lower() in job_desc 
                       for keyword in role_keywords):
                    return {k: v for k, v in worker_info.items() if k != 'worker_instance'}
            
            return None
    
    def delegate_task(self, from_worker_id: str, to_worker_id: str, 
                     task_description: str, **kwargs) -> Dict[str, Any]:
        """
        Delegate a task from one worker to another.
        
        Args:
            from_worker_id: ID of the worker delegating the task
            to_worker_id: ID of the worker receiving the task
            task_description: Description of the task to delegate
            **kwargs: Additional parameters for the task
            
        Returns:
            Result of the delegated task
        """
        with self._lock:
            if to_worker_id not in self.active_workers:
                raise WorkerError(f"Target worker {to_worker_id} not found in registry")
            
            target_worker_info = self.active_workers[to_worker_id]
            target_worker_instance = target_worker_info.get('worker_instance')
            
            if not target_worker_instance:
                raise WorkerError(f"Worker instance not available for {to_worker_id}")
            
            # Update collaboration statistics
            if from_worker_id in self.active_workers:
                self.active_workers[from_worker_id]['collaboration_count'] += 1
            
            # Record collaboration
            collaboration_record = {
                'from_worker': from_worker_id,
                'to_worker': to_worker_id,
                'task_description': task_description,
                'timestamp': datetime.now().isoformat(),
                'parameters': kwargs
            }
            self.collaboration_history.append(collaboration_record)
        
        try:
            # Execute the delegated task
            result = target_worker_instance.call(task_description, **kwargs)
            
            # Update task completion count
            with self._lock:
                if to_worker_id in self.active_workers:
                    self.active_workers[to_worker_id]['tasks_completed'] += 1
            
            return result
            
        except Exception as e:
            raise WorkerError(f"Task delegation failed: {str(e)}")
    
    def get_collaboration_suggestions(self, worker_id: str, task_description: str) -> List[Dict[str, Any]]:
        """
        Get suggestions for which workers could help with a task.
        
        Args:
            worker_id: ID of the worker requesting suggestions
            task_description: Description of the task needing help
            
        Returns:
            List of suggested workers with reasons
        """
        suggestions = []
        task_lower = task_description.lower()
        
        # Keywords that suggest specific types of workers
        role_mappings = {
            'code': ['developer', 'programmer', 'engineer'],
            'design': ['designer', 'creative', 'ui', 'ux'],
            'research': ['researcher', 'analyst', 'investigator'],
            'write': ['writer', 'content', 'documentation'],
            'marketing': ['marketing', 'promotion', 'social'],
            'data': ['data', 'analyst', 'scientist'],
            'test': ['tester', 'qa', 'quality'],
            'manage': ['manager', 'coordinator', 'lead']
        }
        
        # Find relevant workers based on task keywords
        for task_keyword, role_keywords in role_mappings.items():
            if task_keyword in task_lower:
                worker = self.find_worker_by_role(role_keywords, exclude_worker_id=worker_id)
                if worker:
                    suggestions.append({
                        'worker': worker,
                        'reason': f"Specialized in {task_keyword}-related tasks",
                        'confidence': 0.8
                    })
        
        # If no specific matches, suggest based on capabilities
        if not suggestions:
            active_workers = self.get_active_workers(exclude_worker_id=worker_id)
            for worker in active_workers:
                # Simple scoring based on job description relevance
                job_desc = worker.get('job_description', '').lower()
                relevance_score = sum(1 for word in task_lower.split() if word in job_desc)
                
                if relevance_score > 0:
                    suggestions.append({
                        'worker': worker,
                        'reason': f"Job description matches task requirements",
                        'confidence': min(relevance_score * 0.2, 0.7)
                    })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:3]  # Return top 3 suggestions
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get current status of the worker registry."""
        with self._lock:
            return {
                'total_active_workers': len(self.active_workers),
                'workers': list(self.active_workers.keys()),
                'total_collaborations': len(self.collaboration_history),
                'recent_collaborations': self.collaboration_history[-5:] if self.collaboration_history else []
            }
    
    def update_worker_status(self, worker_id: str, status: str, current_task: str = None):
        """Update a worker's current status and task."""
        with self._lock:
            if worker_id in self.active_workers:
                self.active_workers[worker_id]['status'] = status
                if current_task is not None:
                    self.active_workers[worker_id]['current_task'] = current_task


# Global instance
worker_registry = WorkerRegistry()
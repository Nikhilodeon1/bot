"""
Human-like Memory System

Provides intelligent memory storage that mimics human memory:
- Only stores important, relevant information
- Filters out trivial details automatically
- Provides contextually relevant memories when needed
- Supports collaborative memory sharing between workers
"""

import sqlite3
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from .interfaces import IMemorySystem, MemoryEntry, MemoryType
from .exceptions import MemoryError
import uuid


class MemorySystem(IMemorySystem):
    """
    Memory System with SQLite backend for persistent storage.
    
    Provides tiered memory storage with short-term and long-term capabilities,
    intelligent retrieval, and context-aware memory management.
    """
    
    def __init__(self, storage_backend: str = "sqlite", db_path: str = "memory.db"):
        """
        Initialize memory system with SQLite backend.
        
        Args:
            storage_backend: Storage backend type (currently only "sqlite" supported)
            db_path: Path to SQLite database file
        """
        if storage_backend != "sqlite":
            raise MemoryError(f"Unsupported storage backend: {storage_backend}")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database schema for memory storage."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create memory entries table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS memory_entries (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        relevance_score REAL NOT NULL,
                        tags TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
                
                # Create indexes for efficient querying
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_memory_type 
                    ON memory_entries(memory_type)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON memory_entries(timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_relevance_score 
                    ON memory_entries(relevance_score)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_tags 
                    ON memory_entries(tags)
                ''')
                
                conn.commit()
                
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to initialize database: {str(e)}")
    
    def store_short_term(self, data: Dict[str, Any]) -> None:
        """
        Store data in short-term memory.
        
        Args:
            data: Dictionary containing memory data with keys:
                - content: The actual memory content
                - relevance_score: Optional relevance score (default: 0.5)
                - tags: Optional list of tags (default: empty list)
        """
        self._store_memory_entry(data, MemoryType.SHORT_TERM)
    
    def store_long_term(self, data: Dict[str, Any]) -> None:
        """
        Store data in long-term memory.
        
        Args:
            data: Dictionary containing memory data with keys:
                - content: The actual memory content
                - relevance_score: Optional relevance score (default: 0.5)
                - tags: Optional list of tags (default: empty list)
        """
        self._store_memory_entry(data, MemoryType.LONG_TERM)
    
    def _store_memory_entry(self, data: Dict[str, Any], memory_type: MemoryType) -> None:
        """
        Internal method to store memory entry in database.
        
        Args:
            data: Memory data dictionary
            memory_type: Type of memory (short-term or long-term)
        """
        try:
            # Extract data with defaults
            content = data.get('content', {})
            relevance_score = data.get('relevance_score', 0.5)
            tags = data.get('tags', [])
            
            # Create memory entry
            entry = MemoryEntry.create_new(
                content=content,
                memory_type=memory_type,
                relevance_score=relevance_score,
                tags=tags
            )
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO memory_entries 
                    (id, content, timestamp, memory_type, relevance_score, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry.id,
                    json.dumps(entry.content),
                    entry.timestamp.isoformat(),
                    entry.memory_type.value,
                    entry.relevance_score,
                    json.dumps(entry.tags),
                    now,
                    now
                ))
                
                conn.commit()
                
        except (sqlite3.Error, json.JSONEncodeError) as e:
            raise MemoryError(f"Failed to store memory entry: {str(e)}")
    
    def retrieve_by_query(self, query: str, memory_type: str = "both") -> List[Dict]:
        """
        Retrieve memory entries by query string.
        
        Args:
            query: Search query string
            memory_type: Type of memory to search ("short_term", "long_term", or "both")
            
        Returns:
            List of memory entry dictionaries matching the query
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query based on memory type
                if memory_type == "both":
                    type_condition = ""
                    params = [f"%{query}%", f"%{query}%"]
                elif memory_type in ["short_term", "long_term"]:
                    type_condition = "AND memory_type = ?"
                    params = [f"%{query}%", f"%{query}%", memory_type]
                else:
                    raise MemoryError(f"Invalid memory_type: {memory_type}")
                
                # Search in content and tags
                sql_query = f'''
                    SELECT id, content, timestamp, memory_type, relevance_score, tags
                    FROM memory_entries 
                    WHERE (content LIKE ? OR tags LIKE ?) {type_condition}
                    ORDER BY relevance_score DESC, timestamp DESC
                '''
                
                cursor.execute(sql_query, params)
                rows = cursor.fetchall()
                
                # Convert rows to dictionaries
                results = []
                for row in rows:
                    entry_dict = {
                        'id': row[0],
                        'content': json.loads(row[1]),
                        'timestamp': row[2],
                        'memory_type': row[3],
                        'relevance_score': row[4],
                        'tags': json.loads(row[5])
                    }
                    results.append(entry_dict)
                
                return results
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise MemoryError(f"Failed to retrieve memory entries: {str(e)}")
    
    def clear_short_term(self) -> None:
        """Clear all short-term memory entries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM memory_entries WHERE memory_type = ?",
                    (MemoryType.SHORT_TERM.value,)
                )
                conn.commit()
                
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to clear short-term memory: {str(e)}")
    
    def get_context(self, task_context: str) -> Dict[str, Any]:
        """
        Get contextual memory for a task.
        
        Args:
            task_context: Context string describing the task
            
        Returns:
            Dictionary containing relevant memory context
        """
        try:
            # Retrieve relevant memories based on context
            relevant_memories = self.retrieve_by_query(task_context)
            
            # Organize context by memory type and relevance
            context = {
                'short_term_memories': [],
                'long_term_memories': [],
                'total_entries': len(relevant_memories),
                'context_query': task_context
            }
            
            for memory in relevant_memories:
                if memory['memory_type'] == MemoryType.SHORT_TERM.value:
                    context['short_term_memories'].append(memory)
                else:
                    context['long_term_memories'].append(memory)
            
            # Sort by relevance score
            context['short_term_memories'].sort(
                key=lambda x: x['relevance_score'], reverse=True
            )
            context['long_term_memories'].sort(
                key=lambda x: x['relevance_score'], reverse=True
            )
            
            return context
            
        except Exception as e:
            raise MemoryError(f"Failed to get context: {str(e)}")
    
    def cleanup_old_memories(self, days_threshold: int = 30) -> int:
        """
        Clean up old short-term memories beyond threshold.
        
        Args:
            days_threshold: Number of days after which to remove short-term memories
            
        Returns:
            Number of entries removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count entries to be removed
                cursor.execute('''
                    SELECT COUNT(*) FROM memory_entries 
                    WHERE memory_type = ? AND timestamp < ?
                ''', (MemoryType.SHORT_TERM.value, cutoff_date.isoformat()))
                
                count = cursor.fetchone()[0]
                
                # Remove old short-term memories
                cursor.execute('''
                    DELETE FROM memory_entries 
                    WHERE memory_type = ? AND timestamp < ?
                ''', (MemoryType.SHORT_TERM.value, cutoff_date.isoformat()))
                
                conn.commit()
                return count
                
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to cleanup old memories: {str(e)}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about memory usage.
        
        Returns:
            Dictionary containing memory statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count entries by type
                cursor.execute('''
                    SELECT memory_type, COUNT(*) 
                    FROM memory_entries 
                    GROUP BY memory_type
                ''')
                
                type_counts = dict(cursor.fetchall())
                
                # Get total count
                cursor.execute('SELECT COUNT(*) FROM memory_entries')
                total_count = cursor.fetchone()[0]
                
                # Get average relevance score
                cursor.execute('SELECT AVG(relevance_score) FROM memory_entries')
                avg_relevance = cursor.fetchone()[0] or 0.0
                
                return {
                    'total_entries': total_count,
                    'short_term_count': type_counts.get(MemoryType.SHORT_TERM.value, 0),
                    'long_term_count': type_counts.get(MemoryType.LONG_TERM.value, 0),
                    'average_relevance_score': round(avg_relevance, 3)
                }
                
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to get memory statistics: {str(e)}")
    
    def retrieve_by_context(self, context_keywords: List[str], 
                           memory_type: str = "both", 
                           limit: int = 10) -> List[Dict]:
        """
        Retrieve memory entries by context keywords with intelligent scoring.
        
        Args:
            context_keywords: List of keywords to search for
            memory_type: Type of memory to search ("short_term", "long_term", or "both")
            limit: Maximum number of entries to return
            
        Returns:
            List of memory entry dictionaries ordered by relevance
        """
        try:
            if not context_keywords:
                return []
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query based on memory type
                if memory_type == "both":
                    type_condition = ""
                    base_params = []
                elif memory_type in ["short_term", "long_term"]:
                    type_condition = "WHERE memory_type = ?"
                    base_params = [memory_type]
                else:
                    raise MemoryError(f"Invalid memory_type: {memory_type}")
                
                # Get all entries for scoring
                sql_query = f'''
                    SELECT id, content, timestamp, memory_type, relevance_score, tags
                    FROM memory_entries 
                    {type_condition}
                    ORDER BY timestamp DESC
                '''
                
                cursor.execute(sql_query, base_params)
                rows = cursor.fetchall()
                
                # Score and filter entries
                scored_entries = []
                for row in rows:
                    entry_dict = {
                        'id': row[0],
                        'content': json.loads(row[1]),
                        'timestamp': row[2],
                        'memory_type': row[3],
                        'relevance_score': row[4],
                        'tags': json.loads(row[5])
                    }
                    
                    # Calculate context relevance score
                    context_score = self._calculate_context_relevance(
                        entry_dict, context_keywords
                    )
                    
                    if context_score > 0:
                        entry_dict['context_relevance'] = context_score
                        entry_dict['combined_score'] = (
                            entry_dict['relevance_score'] * 0.6 + context_score * 0.4
                        )
                        scored_entries.append(entry_dict)
                
                # Sort by combined score and return top results
                scored_entries.sort(key=lambda x: x['combined_score'], reverse=True)
                return scored_entries[:limit]
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise MemoryError(f"Failed to retrieve by context: {str(e)}")
    
    def _calculate_context_relevance(self, entry: Dict[str, Any], 
                                   keywords: List[str]) -> float:
        """
        Calculate relevance score based on context keywords.
        
        Args:
            entry: Memory entry dictionary
            keywords: List of context keywords
            
        Returns:
            Relevance score between 0 and 1
        """
        if not keywords:
            return 0.0
        
        # Convert entry content and tags to searchable text
        content_text = json.dumps(entry['content']).lower()
        tags_text = ' '.join(entry['tags']).lower()
        combined_text = f"{content_text} {tags_text}"
        
        # Calculate keyword matches
        matches = 0
        total_keywords = len(keywords)
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in combined_text:
                matches += 1
        
        # Base score from keyword matches
        keyword_score = matches / total_keywords if total_keywords > 0 else 0
        
        # Boost score for exact tag matches
        tag_boost = 0
        for keyword in keywords:
            if keyword.lower() in [tag.lower() for tag in entry['tags']]:
                tag_boost += 0.2
        
        # Time decay factor (newer memories get slight boost)
        try:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            time_diff = datetime.now() - entry_time
            time_decay = max(0.1, 1.0 - (time_diff.days / 365.0))  # Decay over a year
        except (ValueError, TypeError):
            time_decay = 0.5
        
        # Combine scores
        final_score = min(1.0, keyword_score + tag_boost) * time_decay
        return round(final_score, 3)
    
    def retrieve_similar_memories(self, reference_content: Dict[str, Any], 
                                memory_type: str = "both", 
                                limit: int = 5) -> List[Dict]:
        """
        Retrieve memories similar to reference content.
        
        Args:
            reference_content: Reference content to find similar memories for
            memory_type: Type of memory to search ("short_term", "long_term", or "both")
            limit: Maximum number of entries to return
            
        Returns:
            List of similar memory entry dictionaries
        """
        try:
            # Extract keywords from reference content
            reference_text = json.dumps(reference_content).lower()
            # Simple keyword extraction (could be enhanced with NLP)
            keywords = [word.strip('",{}[]():') for word in reference_text.split() 
                       if len(word) > 3 and word.isalpha()]
            
            # Remove duplicates and limit keywords
            unique_keywords = list(set(keywords))[:10]
            
            return self.retrieve_by_context(unique_keywords, memory_type, limit)
            
        except Exception as e:
            raise MemoryError(f"Failed to retrieve similar memories: {str(e)}")
    
    def update_memory_relevance(self, memory_id: str, new_relevance: float) -> None:
        """
        Update the relevance score of a memory entry.
        
        Args:
            memory_id: ID of the memory entry to update
            new_relevance: New relevance score (0.0 to 1.0)
        """
        if not (0.0 <= new_relevance <= 1.0):
            raise MemoryError(f"Relevance score must be between 0.0 and 1.0, got: {new_relevance}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update relevance score and timestamp
                cursor.execute('''
                    UPDATE memory_entries 
                    SET relevance_score = ?, updated_at = ?
                    WHERE id = ?
                ''', (new_relevance, datetime.now().isoformat(), memory_id))
                
                if cursor.rowcount == 0:
                    raise MemoryError(f"Memory entry not found: {memory_id}")
                
                conn.commit()
                
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to update memory relevance: {str(e)}")
    
    def add_memory_tags(self, memory_id: str, new_tags: List[str]) -> None:
        """
        Add tags to an existing memory entry.
        
        Args:
            memory_id: ID of the memory entry
            new_tags: List of tags to add
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current tags
                cursor.execute('SELECT tags FROM memory_entries WHERE id = ?', (memory_id,))
                row = cursor.fetchone()
                
                if not row:
                    raise MemoryError(f"Memory entry not found: {memory_id}")
                
                current_tags = json.loads(row[0])
                
                # Add new tags (avoid duplicates)
                for tag in new_tags:
                    if tag not in current_tags:
                        current_tags.append(tag)
                
                # Update tags
                cursor.execute('''
                    UPDATE memory_entries 
                    SET tags = ?, updated_at = ?
                    WHERE id = ?
                ''', (json.dumps(current_tags), datetime.now().isoformat(), memory_id))
                
                conn.commit()
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise MemoryError(f"Failed to add memory tags: {str(e)}")
    
    def get_memories_by_tag(self, tag: str, memory_type: str = "both") -> List[Dict]:
        """
        Retrieve all memories with a specific tag.
        
        Args:
            tag: Tag to search for
            memory_type: Type of memory to search ("short_term", "long_term", or "both")
            
        Returns:
            List of memory entry dictionaries with the specified tag
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query based on memory type
                if memory_type == "both":
                    type_condition = ""
                    params = [f'%"{tag}"%']
                elif memory_type in ["short_term", "long_term"]:
                    type_condition = "AND memory_type = ?"
                    params = [f'%"{tag}"%', memory_type]
                else:
                    raise MemoryError(f"Invalid memory_type: {memory_type}")
                
                sql_query = f'''
                    SELECT id, content, timestamp, memory_type, relevance_score, tags
                    FROM memory_entries 
                    WHERE tags LIKE ? {type_condition}
                    ORDER BY relevance_score DESC, timestamp DESC
                '''
                
                cursor.execute(sql_query, params)
                rows = cursor.fetchall()
                
                # Convert rows to dictionaries
                results = []
                for row in rows:
                    entry_dict = {
                        'id': row[0],
                        'content': json.loads(row[1]),
                        'timestamp': row[2],
                        'memory_type': row[3],
                        'relevance_score': row[4],
                        'tags': json.loads(row[5])
                    }
                    
                    # Verify tag is actually in the list (JSON search can be imprecise)
                    if tag in entry_dict['tags']:
                        results.append(entry_dict)
                
                return results
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise MemoryError(f"Failed to get memories by tag: {str(e)}")
    
    def consolidate_memories(self, similarity_threshold: float = 0.8) -> int:
        """
        Consolidate similar memories to reduce redundancy.
        
        Args:
            similarity_threshold: Threshold for considering memories similar (0.0 to 1.0)
            
        Returns:
            Number of memories consolidated
        """
        try:
            # This is a simplified consolidation - in practice, you might want
            # more sophisticated similarity detection
            consolidated_count = 0
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all memories for comparison
                cursor.execute('''
                    SELECT id, content, tags, relevance_score, timestamp
                    FROM memory_entries 
                    ORDER BY timestamp DESC
                ''')
                
                memories = cursor.fetchall()
                processed_ids = set()
                
                for i, memory1 in enumerate(memories):
                    if memory1[0] in processed_ids:
                        continue
                    
                    memory1_content = json.loads(memory1[1])
                    memory1_tags = set(json.loads(memory1[2]))
                    
                    for j, memory2 in enumerate(memories[i+1:], i+1):
                        if memory2[0] in processed_ids:
                            continue
                        
                        memory2_content = json.loads(memory2[1])
                        memory2_tags = set(json.loads(memory2[2]))
                        
                        # Simple similarity check based on content keys and tags
                        content_similarity = self._calculate_content_similarity(
                            memory1_content, memory2_content
                        )
                        tag_similarity = len(memory1_tags & memory2_tags) / max(
                            len(memory1_tags | memory2_tags), 1
                        )
                        
                        combined_similarity = (content_similarity + tag_similarity) / 2
                        
                        if combined_similarity >= similarity_threshold:
                            # Keep the one with higher relevance score
                            if memory1[3] >= memory2[3]:  # relevance_score
                                cursor.execute('DELETE FROM memory_entries WHERE id = ?', 
                                             (memory2[0],))
                                processed_ids.add(memory2[0])
                            else:
                                cursor.execute('DELETE FROM memory_entries WHERE id = ?', 
                                             (memory1[0],))
                                processed_ids.add(memory1[0])
                                break
                            
                            consolidated_count += 1
                
                conn.commit()
                return consolidated_count
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise MemoryError(f"Failed to consolidate memories: {str(e)}")
    
    def _calculate_content_similarity(self, content1: Dict[str, Any], 
                                    content2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two content dictionaries.
        
        Args:
            content1: First content dictionary
            content2: Second content dictionary
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Simple similarity based on common keys and values
            keys1 = set(content1.keys())
            keys2 = set(content2.keys())
            
            if not keys1 and not keys2:
                return 1.0
            
            if not keys1 or not keys2:
                return 0.0
            
            # Key similarity
            key_similarity = len(keys1 & keys2) / len(keys1 | keys2)
            
            # Value similarity for common keys
            common_keys = keys1 & keys2
            value_matches = 0
            
            for key in common_keys:
                if str(content1[key]).lower() == str(content2[key]).lower():
                    value_matches += 1
            
            value_similarity = value_matches / max(len(common_keys), 1)
            
            return (key_similarity + value_similarity) / 2
            
        except Exception:
            return 0.0
    
    def is_memory_important(self, content: Dict[str, Any], context: str = "") -> bool:
        """
        Determine if information is important enough to store in memory.
        Uses human-like criteria to filter out trivial information.
        """
        try:
            # Convert content to string for analysis
            content_str = str(content)
            
            # Human-like importance criteria
            importance_indicators = [
                # Names and personal information
                any(word in content_str.lower() for word in ['name', 'called', 'i am', 'my name']),
                
                # Goals and objectives
                any(word in content_str.lower() for word in ['goal', 'objective', 'want to', 'need to', 'plan to']),
                
                # Important facts and data
                any(word in content_str.lower() for word in ['important', 'key', 'critical', 'essential', 'remember']),
                
                # Decisions and outcomes
                any(word in content_str.lower() for word in ['decided', 'concluded', 'result', 'outcome', 'solution']),
                
                # Preferences and requirements
                any(word in content_str.lower() for word in ['prefer', 'like', 'dislike', 'requirement', 'must', 'should']),
                
                # Relationships and connections
                any(word in content_str.lower() for word in ['work with', 'team', 'colleague', 'partner', 'collaborate']),
                
                # Significant events or milestones
                any(word in content_str.lower() for word in ['completed', 'finished', 'achieved', 'milestone', 'deadline']),
            ]
            
            # Filter out trivial information
            trivial_indicators = [
                # Generic responses
                content_str.lower().startswith('i '),
                'hello' in content_str.lower() and len(content_str) < 50,
                'thank you' in content_str.lower() and len(content_str) < 50,
                
                # System messages
                any(word in content_str.lower() for word in ['error', 'loading', 'processing', 'please wait']),
                
                # Very short or generic content
                len(content_str.strip()) < 10,
                content_str.lower() in ['ok', 'yes', 'no', 'sure', 'fine', 'good'],
            ]
            
            # Calculate importance score
            importance_score = sum(importance_indicators)
            trivial_score = sum(trivial_indicators)
            
            # Important if has importance indicators and not trivial
            return importance_score > 0 and trivial_score == 0
            
        except Exception:
            # If evaluation fails, err on the side of storing (better safe than sorry)
            return True
    
    def get_relevant_memories_for_context(self, context: str, max_memories: int = 5) -> str:
        """
        Get the most relevant memories for a given context, formatted for LLM consumption.
        Returns only the essential information needed for the current task.
        """
        try:
            # Retrieve relevant memories
            relevant_memories = self.retrieve_by_query(context, memory_type="both")
            
            # Sort by relevance and recency
            relevant_memories.sort(key=lambda x: (x.get('relevance_score', 0), x.get('timestamp', '')), reverse=True)
            
            # Take only the most relevant memories
            top_memories = relevant_memories[:max_memories]
            
            if not top_memories:
                return "No relevant memories found."
            
            # Format memories for LLM consumption
            memory_context = "Relevant memories:\n"
            for i, memory in enumerate(top_memories, 1):
                content = memory.get('content', {})
                
                # Extract key information from memory
                if isinstance(content, dict):
                    # Look for important fields
                    important_info = []
                    
                    for key, value in content.items():
                        if key in ['user_info', 'preferences', 'goals', 'decisions', 'key_facts', 'name', 'role']:
                            important_info.append(f"{key}: {value}")
                        elif 'important' in key.lower() or 'key' in key.lower():
                            important_info.append(f"{key}: {value}")
                    
                    if important_info:
                        memory_context += f"{i}. {' | '.join(important_info)}\n"
                    else:
                        # Fallback to string representation
                        memory_str = str(content)[:200]
                        if len(memory_str) > 10:  # Only include if meaningful
                            memory_context += f"{i}. {memory_str}\n"
                else:
                    memory_str = str(content)[:200]
                    if len(memory_str) > 10:
                        memory_context += f"{i}. {memory_str}\n"
            
            return memory_context.strip()
            
        except Exception as e:
            return f"Error retrieving memories: {str(e)}"
    
    def store_important_fact(self, fact: str, category: str = "general", context: str = ""):
        """
        Store an important fact in memory with proper categorization.
        Only stores if the fact is deemed important by human-like criteria.
        """
        try:
            # Check if this fact is important enough to store
            fact_data = {
                'fact': fact,
                'category': category,
                'context': context,
                'stored_at': datetime.now().isoformat()
            }
            
            if self.is_memory_important(fact_data, context):
                # Store as long-term memory since it's an important fact
                self.store_long_term({
                    'content': fact_data,
                    'relevance_score': 0.8,  # Important facts get high relevance
                    'tags': [category, 'important_fact', 'user_provided']
                })
                return True
            else:
                # Fact not important enough to store
                return False
                
        except Exception:
            return False

    def close(self) -> None:
        """
        Close database connections and cleanup resources.
        
        This method ensures proper cleanup of database connections,
        particularly important on Windows systems.
        """
        # SQLite connections are automatically closed when the connection
        # object is garbage collected, but we can force cleanup here if needed
        pass
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.close()
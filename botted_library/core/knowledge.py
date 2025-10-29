"""
Knowledge validation system for the Botted Library

Provides source reliability tracking, accuracy checking, and cross-referencing capabilities.
"""

import sqlite3
import json
import hashlib
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import logging

from .interfaces import IKnowledgeValidator
from .exceptions import ValidationError, ConfigurationError


@dataclass
class SourceReliability:
    """Data model for source reliability information"""
    source: str
    reliability_score: float
    validation_count: int
    last_updated: datetime
    source_type: str
    reputation_factors: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['last_updated'] = self.last_updated.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceReliability':
        """Create from dictionary"""
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


@dataclass
class AccuracyScore:
    """Data model for accuracy assessment results"""
    score: float
    confidence: float
    validation_method: str
    cross_references: List[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccuracyScore':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ValidationResult:
    """Data model for cross-reference validation results"""
    source: str
    content_match: float
    reliability_weight: float
    validation_timestamp: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['validation_timestamp'] = self.validation_timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationResult':
        """Create from dictionary"""
        data['validation_timestamp'] = datetime.fromisoformat(data['validation_timestamp'])
        return cls(**data)


class KnowledgeValidator(IKnowledgeValidator):
    """
    Knowledge validation system that tracks source reliability and validates information accuracy.
    
    Provides methods for:
    - Source reliability tracking and scoring
    - Information accuracy checking with confidence scoring
    - Cross-referencing capabilities for validation
    - Dynamic learning and adaptation of source trustworthiness
    """

    def __init__(self, db_path: str = "knowledge_validation.db", 
                 trusted_sources: Optional[List[str]] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize the knowledge validation system.
        
        Args:
            db_path: Path to SQLite database for persistence
            trusted_sources: Initial list of trusted source domains/URLs
            config: Configuration parameters for validation algorithms
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.config = {
            'min_reliability_threshold': 0.3,
            'max_reliability_score': 1.0,
            'reliability_decay_factor': 0.95,
            'cross_reference_threshold': 0.7,
            'accuracy_confidence_threshold': 0.6,
            'source_validation_window_days': 30,
            'max_cross_references': 10
        }
        
        if config:
            self.config.update(config)
        
        # Initialize trusted sources
        self.trusted_sources = set(trusted_sources or [
            'wikipedia.org',
            'britannica.com',
            'nature.com',
            'sciencedirect.com',
            'pubmed.ncbi.nlm.nih.gov',
            'arxiv.org'
        ])
        
        # Initialize database
        self._init_database()
        
        # Initialize default source reliabilities
        self._initialize_trusted_sources()

    def _init_database(self) -> None:
        """Initialize SQLite database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Source reliability table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS source_reliability (
                        source TEXT PRIMARY KEY,
                        reliability_score REAL NOT NULL,
                        validation_count INTEGER DEFAULT 0,
                        last_updated TEXT NOT NULL,
                        source_type TEXT DEFAULT 'unknown',
                        reputation_factors TEXT DEFAULT '{}'
                    )
                ''')
                
                # Validation history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS validation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        information_hash TEXT NOT NULL,
                        accuracy_score REAL NOT NULL,
                        confidence_score REAL NOT NULL,
                        validation_method TEXT NOT NULL,
                        cross_references TEXT DEFAULT '[]',
                        timestamp TEXT NOT NULL,
                        metadata TEXT DEFAULT '{}'
                    )
                ''')
                
                # Cross-reference cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cross_reference_cache (
                        information_hash TEXT PRIMARY KEY,
                        cross_references TEXT NOT NULL,
                        last_updated TEXT NOT NULL,
                        expiry_date TEXT NOT NULL
                    )
                ''')
                
                conn.commit()
                
        except sqlite3.Error as e:
            raise ConfigurationError(
                "Failed to initialize knowledge validation database",
                config_key="db_path",
                config_value=self.db_path,
                original_exception=e
            )

    def _initialize_trusted_sources(self) -> None:
        """Initialize trusted sources with high reliability scores"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for source in self.trusted_sources:
                    cursor.execute('''
                        INSERT OR IGNORE INTO source_reliability 
                        (source, reliability_score, validation_count, last_updated, source_type, reputation_factors)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        source,
                        0.9,  # High initial reliability for trusted sources
                        0,
                        datetime.now().isoformat(),
                        'trusted',
                        json.dumps({'initial_trust': 0.9, 'domain_reputation': 0.95})
                    ))
                
                conn.commit()
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize trusted sources: {e}")

    def validate_source(self, source: str) -> float:
        """
        Validate source reliability and return reliability score.
        
        Args:
            source: Source URL or domain to validate
            
        Returns:
            Reliability score between 0.0 and 1.0
        """
        try:
            # Normalize source (extract domain if URL)
            normalized_source = self._normalize_source(source)
            
            # Check database for existing reliability score
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT reliability_score, validation_count, last_updated, reputation_factors FROM source_reliability WHERE source = ?',
                    (normalized_source,)
                )
                result = cursor.fetchone()
                
                if result:
                    reliability_score, validation_count, last_updated_str, reputation_factors_str = result
                    last_updated = datetime.fromisoformat(last_updated_str)
                    reputation_factors = json.loads(reputation_factors_str)
                    
                    # Apply time-based decay if source hasn't been validated recently
                    days_since_update = (datetime.now() - last_updated).days
                    if days_since_update > self.config['source_validation_window_days']:
                        decay_factor = self.config['reliability_decay_factor'] ** (days_since_update / 30)
                        reliability_score *= decay_factor
                        
                        # Update database with decayed score
                        cursor.execute('''
                            UPDATE source_reliability 
                            SET reliability_score = ?, last_updated = ?
                            WHERE source = ?
                        ''', (reliability_score, datetime.now().isoformat(), normalized_source))
                        conn.commit()
                    
                    return min(reliability_score, self.config['max_reliability_score'])
                
                else:
                    # New source - calculate initial reliability
                    initial_reliability = self._calculate_initial_reliability(normalized_source)
                    
                    # Store in database
                    cursor.execute('''
                        INSERT INTO source_reliability 
                        (source, reliability_score, validation_count, last_updated, source_type, reputation_factors)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        normalized_source,
                        initial_reliability,
                        0,
                        datetime.now().isoformat(),
                        self._classify_source_type(normalized_source),
                        json.dumps(self._calculate_reputation_factors(normalized_source))
                    ))
                    conn.commit()
                    
                    return initial_reliability
                    
        except Exception as e:
            raise ValidationError(
                "Failed to validate source reliability",
                source=source,
                validation_type="source_reliability",
                original_exception=e
            )

    def check_accuracy(self, data: str, context: str) -> float:
        """
        Check data accuracy and return accuracy score.
        
        Args:
            data: Information to validate
            context: Context for the information
            
        Returns:
            Accuracy score between 0.0 and 1.0
        """
        try:
            # Generate hash for the information
            info_hash = self._generate_info_hash(data, context)
            
            # Check for cached validation results
            cached_result = self._get_cached_validation(info_hash)
            if cached_result:
                return cached_result.score
            
            # Perform cross-referencing
            cross_references = self.cross_reference(data)
            
            if not cross_references:
                # No cross-references found - return low confidence score
                accuracy_score = 0.3
                confidence = 0.2
            else:
                # Calculate accuracy based on cross-references
                accuracy_score, confidence = self._calculate_accuracy_from_references(
                    data, cross_references
                )
            
            # Store validation result
            self._store_validation_result(
                info_hash, data, accuracy_score, confidence, cross_references, context
            )
            
            return accuracy_score
            
        except Exception as e:
            raise ValidationError(
                "Failed to check information accuracy",
                validation_type="accuracy_check",
                original_exception=e
            )

    def cross_reference(self, information: str) -> List[Dict[str, Any]]:
        """
        Cross-reference information against known sources.
        
        Args:
            information: Information to cross-reference
            
        Returns:
            List of validation results from cross-referencing
        """
        try:
            # Generate hash for caching
            info_hash = self._generate_info_hash(information, "")
            
            # Check cache first
            cached_references = self._get_cached_cross_references(info_hash)
            if cached_references:
                return cached_references
            
            # Perform cross-referencing
            validation_results = []
            
            # Get reliable sources for cross-referencing
            reliable_sources = self._get_reliable_sources()
            
            for source_data in reliable_sources[:self.config['max_cross_references']]:
                source = source_data['source']
                reliability = source_data['reliability_score']
                
                # Simulate content matching (in real implementation, this would
                # involve actual web scraping or API calls)
                content_match = self._simulate_content_matching(information, source)
                
                if content_match > 0.1:  # Only include meaningful matches
                    validation_result = ValidationResult(
                        source=source,
                        content_match=content_match,
                        reliability_weight=reliability,
                        validation_timestamp=datetime.now(),
                        metadata={
                            'matching_method': 'simulated',
                            'information_length': len(information),
                            'source_type': source_data.get('source_type', 'unknown')
                        }
                    )
                    validation_results.append(validation_result.to_dict())
            
            # Cache the results
            self._cache_cross_references(info_hash, validation_results)
            
            return validation_results
            
        except Exception as e:
            raise ValidationError(
                "Failed to cross-reference information",
                validation_type="cross_reference",
                original_exception=e
            )

    def update_source_reliability(self, source: str, reliability: float) -> None:
        """
        Update source reliability based on validation results.
        
        Args:
            source: Source to update
            reliability: New reliability score (0.0 to 1.0)
        """
        try:
            if not 0.0 <= reliability <= 1.0:
                raise ValidationError(
                    "Reliability score must be between 0.0 and 1.0",
                    source=source,
                    confidence_score=reliability
                )
            
            normalized_source = self._normalize_source(source)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current reliability data
                cursor.execute(
                    'SELECT reliability_score, validation_count, reputation_factors FROM source_reliability WHERE source = ?',
                    (normalized_source,)
                )
                result = cursor.fetchone()
                
                if result:
                    current_score, validation_count, reputation_factors_str = result
                    reputation_factors = json.loads(reputation_factors_str)
                    
                    # Calculate weighted average with validation count
                    weight = min(validation_count + 1, 10) / 10  # Cap influence at 10 validations
                    new_score = (current_score * weight + reliability * (1 - weight))
                    
                    # Update reputation factors
                    reputation_factors['recent_validation'] = reliability
                    reputation_factors['validation_trend'] = reliability - current_score
                    
                    # Update database
                    cursor.execute('''
                        UPDATE source_reliability 
                        SET reliability_score = ?, validation_count = ?, last_updated = ?, reputation_factors = ?
                        WHERE source = ?
                    ''', (
                        new_score,
                        validation_count + 1,
                        datetime.now().isoformat(),
                        json.dumps(reputation_factors),
                        normalized_source
                    ))
                    
                else:
                    # Create new entry
                    cursor.execute('''
                        INSERT INTO source_reliability 
                        (source, reliability_score, validation_count, last_updated, source_type, reputation_factors)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        normalized_source,
                        reliability,
                        1,
                        datetime.now().isoformat(),
                        self._classify_source_type(normalized_source),
                        json.dumps({'initial_validation': reliability})
                    ))
                
                conn.commit()
                
        except Exception as e:
            raise ValidationError(
                "Failed to update source reliability",
                source=source,
                confidence_score=reliability,
                original_exception=e
            )

    def _normalize_source(self, source: str) -> str:
        """Normalize source URL to domain"""
        try:
            if source.startswith(('http://', 'https://')):
                parsed = urlparse(source)
                return parsed.netloc.lower()
            else:
                return source.lower().strip()
        except Exception:
            return source.lower().strip()

    def _classify_source_type(self, source: str) -> str:
        """Classify source type based on domain patterns"""
        source_lower = source.lower()
        
        if any(edu in source_lower for edu in ['.edu', '.ac.', 'university', 'college']):
            return 'academic'
        elif any(gov in source_lower for gov in ['.gov', '.mil']):
            return 'government'
        elif any(news in source_lower for news in ['news', 'times', 'post', 'guardian', 'reuters']):
            return 'news'
        elif any(wiki in source_lower for wiki in ['wiki', 'encyclopedia']):
            return 'reference'
        elif any(sci in source_lower for sci in ['nature', 'science', 'pubmed', 'arxiv']):
            return 'scientific'
        else:
            return 'general'

    def _calculate_initial_reliability(self, source: str) -> float:
        """Calculate initial reliability score for new sources"""
        base_score = 0.5  # Neutral starting point
        
        # Adjust based on source type
        source_type = self._classify_source_type(source)
        type_bonuses = {
            'academic': 0.3,
            'government': 0.25,
            'scientific': 0.35,
            'reference': 0.2,
            'news': 0.1,
            'general': 0.0
        }
        
        base_score += type_bonuses.get(source_type, 0.0)
        
        # Check if it's in trusted sources
        if source in self.trusted_sources:
            base_score += 0.2
        
        return min(base_score, self.config['max_reliability_score'])

    def _calculate_reputation_factors(self, source: str) -> Dict[str, float]:
        """Calculate reputation factors for a source"""
        return {
            'domain_age_factor': 0.5,  # Would be calculated from domain registration
            'ssl_security_factor': 0.8,  # Would check SSL certificate
            'content_quality_factor': 0.6,  # Would analyze content patterns
            'citation_factor': 0.5,  # Would check how often source is cited
            'source_type_factor': 0.7  # Based on source classification
        }

    def _generate_info_hash(self, information: str, context: str) -> str:
        """Generate hash for information caching"""
        combined = f"{information.strip().lower()}|{context.strip().lower()}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_cached_validation(self, info_hash: str) -> Optional[AccuracyScore]:
        """Get cached validation result"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT accuracy_score, confidence_score, validation_method, cross_references, timestamp
                    FROM validation_history 
                    WHERE information_hash = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (info_hash,))
                
                result = cursor.fetchone()
                if result:
                    accuracy, confidence, method, refs_str, timestamp_str = result
                    return AccuracyScore(
                        score=accuracy,
                        confidence=confidence,
                        validation_method=method,
                        cross_references=json.loads(refs_str),
                        timestamp=datetime.fromisoformat(timestamp_str)
                    )
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to get cached validation: {e}")
            return None

    def _get_cached_cross_references(self, info_hash: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached cross-reference results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT cross_references, expiry_date
                    FROM cross_reference_cache 
                    WHERE information_hash = ?
                ''', (info_hash,))
                
                result = cursor.fetchone()
                if result:
                    refs_str, expiry_str = result
                    expiry = datetime.fromisoformat(expiry_str)
                    
                    if datetime.now() < expiry:
                        return json.loads(refs_str)
                    else:
                        # Remove expired cache entry
                        cursor.execute('DELETE FROM cross_reference_cache WHERE information_hash = ?', (info_hash,))
                        conn.commit()
                
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to get cached cross-references: {e}")
            return None

    def _cache_cross_references(self, info_hash: str, references: List[Dict[str, Any]]) -> None:
        """Cache cross-reference results"""
        try:
            expiry = datetime.now() + timedelta(hours=24)  # Cache for 24 hours
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO cross_reference_cache 
                    (information_hash, cross_references, last_updated, expiry_date)
                    VALUES (?, ?, ?, ?)
                ''', (
                    info_hash,
                    json.dumps(references),
                    datetime.now().isoformat(),
                    expiry.isoformat()
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.warning(f"Failed to cache cross-references: {e}")

    def _get_reliable_sources(self) -> List[Dict[str, Any]]:
        """Get list of reliable sources for cross-referencing"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT source, reliability_score, source_type
                    FROM source_reliability 
                    WHERE reliability_score >= ?
                    ORDER BY reliability_score DESC
                ''', (self.config['cross_reference_threshold'],))
                
                results = cursor.fetchall()
                return [
                    {
                        'source': source,
                        'reliability_score': reliability,
                        'source_type': source_type
                    }
                    for source, reliability, source_type in results
                ]
                
        except Exception as e:
            self.logger.error(f"Failed to get reliable sources: {e}")
            return []

    def _simulate_content_matching(self, information: str, source: str) -> float:
        """
        Simulate content matching between information and source.
        In a real implementation, this would involve web scraping or API calls.
        """
        # Simple simulation based on information length and source reliability
        info_words = len(information.split())
        
        # Simulate higher match probability for academic/scientific sources
        source_type = self._classify_source_type(source)
        base_match = {
            'academic': 0.7,
            'scientific': 0.8,
            'government': 0.6,
            'reference': 0.75,
            'news': 0.4,
            'general': 0.3
        }.get(source_type, 0.3)
        
        # Adjust based on information complexity
        if info_words > 50:
            base_match *= 0.8  # Longer information is harder to match
        elif info_words < 10:
            base_match *= 0.6  # Very short information is less reliable
        
        # Add some randomness to simulate real-world variation
        import random
        random.seed(hash(information + source) % 1000)  # Deterministic randomness
        variation = random.uniform(-0.2, 0.2)
        
        return max(0.0, min(1.0, base_match + variation))

    def _calculate_accuracy_from_references(self, information: str, 
                                         references: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Calculate accuracy score and confidence from cross-references"""
        if not references:
            return 0.3, 0.2
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for ref in references:
            content_match = ref['content_match']
            reliability_weight = ref['reliability_weight']
            
            # Weight the content match by source reliability
            weighted_score = content_match * reliability_weight
            total_weighted_score += weighted_score
            total_weight += reliability_weight
        
        if total_weight == 0:
            return 0.3, 0.2
        
        # Calculate weighted average accuracy
        accuracy = total_weighted_score / total_weight
        
        # Calculate confidence based on number of references and their agreement
        reference_count_factor = min(len(references) / 5.0, 1.0)  # Max confidence at 5+ references
        agreement_factor = self._calculate_reference_agreement(references)
        
        confidence = (reference_count_factor * 0.6 + agreement_factor * 0.4)
        
        return accuracy, confidence

    def _calculate_reference_agreement(self, references: List[Dict[str, Any]]) -> float:
        """Calculate how much the references agree with each other"""
        if len(references) < 2:
            return 0.5
        
        matches = [ref['content_match'] for ref in references]
        
        # Calculate variance in matches (lower variance = higher agreement)
        mean_match = sum(matches) / len(matches)
        variance = sum((match - mean_match) ** 2 for match in matches) / len(matches)
        
        # Convert variance to agreement score (0-1, where 1 is perfect agreement)
        agreement = max(0.0, 1.0 - variance * 2)  # Scale variance appropriately
        
        return agreement

    def _store_validation_result(self, info_hash: str, information: str, 
                               accuracy: float, confidence: float,
                               cross_references: List[Dict[str, Any]], context: str) -> None:
        """Store validation result in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO validation_history 
                    (source, information_hash, accuracy_score, confidence_score, 
                     validation_method, cross_references, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'cross_reference',  # Source is the validation method in this case
                    info_hash,
                    accuracy,
                    confidence,
                    'cross_reference_analysis',
                    json.dumps([ref['source'] for ref in cross_references]),
                    datetime.now().isoformat(),
                    json.dumps({
                        'context': context,
                        'information_length': len(information),
                        'reference_count': len(cross_references)
                    })
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.warning(f"Failed to store validation result: {e}")

    def get_source_statistics(self) -> Dict[str, Any]:
        """Get statistics about tracked sources"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total sources
                cursor.execute('SELECT COUNT(*) FROM source_reliability')
                total_sources = cursor.fetchone()[0]
                
                # Reliable sources (above threshold)
                cursor.execute(
                    'SELECT COUNT(*) FROM source_reliability WHERE reliability_score >= ?',
                    (self.config['cross_reference_threshold'],)
                )
                reliable_sources = cursor.fetchone()[0]
                
                # Average reliability
                cursor.execute('SELECT AVG(reliability_score) FROM source_reliability')
                avg_reliability = cursor.fetchone()[0] or 0.0
                
                # Source types distribution
                cursor.execute('SELECT source_type, COUNT(*) FROM source_reliability GROUP BY source_type')
                source_types = dict(cursor.fetchall())
                
                return {
                    'total_sources': total_sources,
                    'reliable_sources': reliable_sources,
                    'average_reliability': round(avg_reliability, 3),
                    'source_types': source_types,
                    'reliability_threshold': self.config['cross_reference_threshold']
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get source statistics: {e}")
            return {}

    def add_trusted_source(self, source: str, initial_reliability: float = 0.8) -> None:
        """
        Add a new trusted source to the system.
        
        Args:
            source: Source URL or domain to add
            initial_reliability: Initial reliability score (default 0.8)
        """
        try:
            if not 0.0 <= initial_reliability <= 1.0:
                raise ValidationError(
                    "Initial reliability must be between 0.0 and 1.0",
                    source=source,
                    confidence_score=initial_reliability
                )
            
            normalized_source = self._normalize_source(source)
            self.trusted_sources.add(normalized_source)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO source_reliability 
                    (source, reliability_score, validation_count, last_updated, source_type, reputation_factors)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    normalized_source,
                    initial_reliability,
                    0,
                    datetime.now().isoformat(),
                    'trusted',
                    json.dumps({'manually_added': True, 'initial_trust': initial_reliability})
                ))
                conn.commit()
                
            self.logger.info(f"Added trusted source: {normalized_source}")
            
        except Exception as e:
            raise ValidationError(
                "Failed to add trusted source",
                source=source,
                original_exception=e
            )

    def remove_trusted_source(self, source: str) -> None:
        """
        Remove a source from the trusted sources list.
        
        Args:
            source: Source URL or domain to remove
        """
        try:
            normalized_source = self._normalize_source(source)
            self.trusted_sources.discard(normalized_source)
            
            # Update source type in database but don't delete the reliability data
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE source_reliability 
                    SET source_type = ?, last_updated = ?
                    WHERE source = ? AND source_type = 'trusted'
                ''', (
                    self._classify_source_type(normalized_source),
                    datetime.now().isoformat(),
                    normalized_source
                ))
                conn.commit()
                
            self.logger.info(f"Removed trusted source: {normalized_source}")
            
        except Exception as e:
            raise ValidationError(
                "Failed to remove trusted source",
                source=source,
                original_exception=e
            )

    def blacklist_source(self, source: str, reason: str = "") -> None:
        """
        Blacklist a source as unreliable.
        
        Args:
            source: Source URL or domain to blacklist
            reason: Reason for blacklisting
        """
        try:
            normalized_source = self._normalize_source(source)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Set very low reliability and mark as blacklisted
                reputation_factors = {
                    'blacklisted': True,
                    'blacklist_reason': reason,
                    'blacklist_date': datetime.now().isoformat()
                }
                
                cursor.execute('''
                    INSERT OR REPLACE INTO source_reliability 
                    (source, reliability_score, validation_count, last_updated, source_type, reputation_factors)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    normalized_source,
                    0.05,  # Very low reliability for blacklisted sources
                    0,
                    datetime.now().isoformat(),
                    'blacklisted',
                    json.dumps(reputation_factors)
                ))
                conn.commit()
                
            self.logger.info(f"Blacklisted source: {normalized_source} - {reason}")
            
        except Exception as e:
            raise ValidationError(
                "Failed to blacklist source",
                source=source,
                original_exception=e
            )

    def get_source_reputation(self, source: str) -> Dict[str, Any]:
        """
        Get detailed reputation information for a source.
        
        Args:
            source: Source URL or domain
            
        Returns:
            Dictionary containing reputation details
        """
        try:
            normalized_source = self._normalize_source(source)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT reliability_score, validation_count, last_updated, 
                           source_type, reputation_factors
                    FROM source_reliability 
                    WHERE source = ?
                ''', (normalized_source,))
                
                result = cursor.fetchone()
                if not result:
                    return {
                        'source': normalized_source,
                        'reliability_score': None,
                        'status': 'unknown',
                        'validation_count': 0,
                        'last_updated': None,
                        'source_type': 'unknown',
                        'reputation_factors': {}
                    }
                
                reliability, validation_count, last_updated_str, source_type, reputation_str = result
                reputation_factors = json.loads(reputation_str)
                
                # Get validation history
                cursor.execute('''
                    SELECT accuracy_score, confidence_score, timestamp
                    FROM validation_history 
                    WHERE source = ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                ''', (normalized_source,))
                
                validation_history = [
                    {
                        'accuracy': acc,
                        'confidence': conf,
                        'timestamp': ts
                    }
                    for acc, conf, ts in cursor.fetchall()
                ]
                
                # Determine status
                status = 'reliable' if reliability >= self.config['cross_reference_threshold'] else 'unreliable'
                if source_type == 'blacklisted':
                    status = 'blacklisted'
                elif source_type == 'trusted':
                    status = 'trusted'
                
                return {
                    'source': normalized_source,
                    'reliability_score': reliability,
                    'status': status,
                    'validation_count': validation_count,
                    'last_updated': last_updated_str,
                    'source_type': source_type,
                    'reputation_factors': reputation_factors,
                    'validation_history': validation_history
                }
                
        except Exception as e:
            raise ValidationError(
                "Failed to get source reputation",
                source=source,
                original_exception=e
            )

    def learn_from_validation_feedback(self, source: str, information: str, 
                                     user_feedback: str, confidence: float = 1.0) -> None:
        """
        Learn from user feedback about validation accuracy.
        
        Args:
            source: Source that provided the information
            information: The information that was validated
            user_feedback: User feedback ('correct', 'incorrect', 'partially_correct')
            confidence: Confidence in the user feedback (0.0 to 1.0)
        """
        try:
            if user_feedback not in ['correct', 'incorrect', 'partially_correct']:
                raise ValidationError(
                    "User feedback must be 'correct', 'incorrect', or 'partially_correct'",
                    source=source,
                    validation_type="user_feedback"
                )
            
            if not 0.0 <= confidence <= 1.0:
                raise ValidationError(
                    "Confidence must be between 0.0 and 1.0",
                    source=source,
                    confidence_score=confidence
                )
            
            # Convert feedback to reliability adjustment
            feedback_scores = {
                'correct': 0.9,
                'partially_correct': 0.6,
                'incorrect': 0.1
            }
            
            feedback_reliability = feedback_scores[user_feedback] * confidence
            
            # Update source reliability with learning
            self._update_source_with_learning(source, feedback_reliability, user_feedback)
            
            # Store feedback for future learning
            self._store_learning_feedback(source, information, user_feedback, confidence)
            
            self.logger.info(f"Learned from feedback for {source}: {user_feedback} (confidence: {confidence})")
            
        except Exception as e:
            raise ValidationError(
                "Failed to learn from validation feedback",
                source=source,
                validation_type="learning_feedback",
                original_exception=e
            )

    def adapt_validation_thresholds(self) -> None:
        """
        Adapt validation thresholds based on historical performance.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Analyze validation performance over time
                cursor.execute('''
                    SELECT AVG(accuracy_score), AVG(confidence_score), COUNT(*)
                    FROM validation_history 
                    WHERE timestamp > ?
                ''', ((datetime.now() - timedelta(days=30)).isoformat(),))
                
                result = cursor.fetchone()
                if result and result[2] > 10:  # Need at least 10 validations
                    avg_accuracy, avg_confidence, count = result
                    
                    # Adjust thresholds based on performance
                    if avg_accuracy > 0.8 and avg_confidence > 0.7:
                        # High performance - can be more selective
                        self.config['cross_reference_threshold'] = min(
                            self.config['cross_reference_threshold'] + 0.05, 0.9
                        )
                    elif avg_accuracy < 0.6 or avg_confidence < 0.5:
                        # Low performance - be less selective
                        self.config['cross_reference_threshold'] = max(
                            self.config['cross_reference_threshold'] - 0.05, 0.3
                        )
                    
                    self.logger.info(f"Adapted cross-reference threshold to {self.config['cross_reference_threshold']}")
                
        except Exception as e:
            self.logger.error(f"Failed to adapt validation thresholds: {e}")

    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get statistics about the learning system performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get feedback statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_feedback,
                        AVG(CASE WHEN metadata LIKE '%correct%' THEN 1.0 ELSE 0.0 END) as accuracy_rate,
                        COUNT(DISTINCT source) as sources_with_feedback
                    FROM validation_history 
                    WHERE validation_method = 'user_feedback'
                    AND timestamp > ?
                ''', ((datetime.now() - timedelta(days=30)).isoformat(),))
                
                feedback_stats = cursor.fetchone()
                
                # Get source improvement statistics
                cursor.execute('''
                    SELECT 
                        source,
                        MIN(reliability_score) as min_reliability,
                        MAX(reliability_score) as max_reliability,
                        validation_count
                    FROM source_reliability 
                    WHERE validation_count > 0
                    GROUP BY source
                    HAVING MAX(reliability_score) - MIN(reliability_score) > 0.1
                ''')
                
                improving_sources = cursor.fetchall()
                
                return {
                    'total_feedback_received': feedback_stats[0] if feedback_stats else 0,
                    'feedback_accuracy_rate': round(feedback_stats[1] or 0.0, 3),
                    'sources_with_feedback': feedback_stats[2] if feedback_stats else 0,
                    'improving_sources_count': len(improving_sources),
                    'current_thresholds': {
                        'cross_reference_threshold': self.config['cross_reference_threshold'],
                        'accuracy_confidence_threshold': self.config['accuracy_confidence_threshold']
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get learning statistics: {e}")
            return {}

    def _update_source_with_learning(self, source: str, feedback_reliability: float, 
                                   feedback_type: str) -> None:
        """Update source reliability using learning algorithms"""
        try:
            normalized_source = self._normalize_source(source)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current reliability data
                cursor.execute('''
                    SELECT reliability_score, validation_count, reputation_factors
                    FROM source_reliability 
                    WHERE source = ?
                ''', (normalized_source,))
                
                result = cursor.fetchone()
                if result:
                    current_score, validation_count, reputation_str = result
                    reputation_factors = json.loads(reputation_str)
                    
                    # Apply learning rate based on validation count
                    learning_rate = max(0.1, 1.0 / (validation_count + 1))
                    
                    # Calculate new reliability using exponential moving average
                    new_reliability = (
                        current_score * (1 - learning_rate) + 
                        feedback_reliability * learning_rate
                    )
                    
                    # Update reputation factors with learning data
                    reputation_factors['last_feedback'] = feedback_type
                    reputation_factors['feedback_count'] = reputation_factors.get('feedback_count', 0) + 1
                    reputation_factors['learning_rate'] = learning_rate
                    
                    # Update database
                    cursor.execute('''
                        UPDATE source_reliability 
                        SET reliability_score = ?, validation_count = ?, 
                            last_updated = ?, reputation_factors = ?
                        WHERE source = ?
                    ''', (
                        new_reliability,
                        validation_count + 1,
                        datetime.now().isoformat(),
                        json.dumps(reputation_factors),
                        normalized_source
                    ))
                    
                else:
                    # Create new entry with feedback
                    reputation_factors = {
                        'first_feedback': feedback_type,
                        'feedback_count': 1,
                        'learning_rate': 1.0
                    }
                    
                    cursor.execute('''
                        INSERT INTO source_reliability 
                        (source, reliability_score, validation_count, last_updated, source_type, reputation_factors)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        normalized_source,
                        feedback_reliability,
                        1,
                        datetime.now().isoformat(),
                        self._classify_source_type(normalized_source),
                        json.dumps(reputation_factors)
                    ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update source with learning: {e}")

    def _store_learning_feedback(self, source: str, information: str, 
                               feedback: str, confidence: float) -> None:
        """Store user feedback for learning purposes"""
        try:
            info_hash = self._generate_info_hash(information, "user_feedback")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO validation_history 
                    (source, information_hash, accuracy_score, confidence_score, 
                     validation_method, cross_references, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self._normalize_source(source),
                    info_hash,
                    1.0 if feedback == 'correct' else 0.5 if feedback == 'partially_correct' else 0.0,
                    confidence,
                    'user_feedback',
                    json.dumps([source]),
                    datetime.now().isoformat(),
                    json.dumps({
                        'feedback_type': feedback,
                        'information_length': len(information),
                        'learning_event': True
                    })
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.warning(f"Failed to store learning feedback: {e}")

    def export_source_database(self) -> Dict[str, Any]:
        """Export the source reliability database for backup or analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Export source reliability data
                cursor.execute('SELECT * FROM source_reliability')
                sources = []
                for row in cursor.fetchall():
                    sources.append({
                        'source': row[0],
                        'reliability_score': row[1],
                        'validation_count': row[2],
                        'last_updated': row[3],
                        'source_type': row[4],
                        'reputation_factors': json.loads(row[5])
                    })
                
                # Export validation history summary
                cursor.execute('''
                    SELECT source, COUNT(*), AVG(accuracy_score), AVG(confidence_score)
                    FROM validation_history 
                    GROUP BY source
                ''')
                
                validation_summary = []
                for row in cursor.fetchall():
                    validation_summary.append({
                        'source': row[0],
                        'validation_count': row[1],
                        'avg_accuracy': row[2],
                        'avg_confidence': row[3]
                    })
                
                return {
                    'export_timestamp': datetime.now().isoformat(),
                    'total_sources': len(sources),
                    'sources': sources,
                    'validation_summary': validation_summary,
                    'config': self.config,
                    'trusted_sources': list(self.trusted_sources)
                }
                
        except Exception as e:
            raise ValidationError(
                "Failed to export source database",
                validation_type="database_export",
                original_exception=e
            )

    def import_source_database(self, data: Dict[str, Any], merge: bool = True) -> None:
        """
        Import source reliability database from exported data.
        
        Args:
            data: Exported database data
            merge: If True, merge with existing data; if False, replace
        """
        try:
            if not merge:
                # Clear existing data
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM source_reliability')
                    cursor.execute('DELETE FROM validation_history')
                    cursor.execute('DELETE FROM cross_reference_cache')
                    conn.commit()
            
            # Import sources
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for source_data in data.get('sources', []):
                    cursor.execute('''
                        INSERT OR REPLACE INTO source_reliability 
                        (source, reliability_score, validation_count, last_updated, source_type, reputation_factors)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        source_data['source'],
                        source_data['reliability_score'],
                        source_data['validation_count'],
                        source_data['last_updated'],
                        source_data['source_type'],
                        json.dumps(source_data['reputation_factors'])
                    ))
                
                conn.commit()
            
            # Update trusted sources
            if 'trusted_sources' in data:
                self.trusted_sources.update(data['trusted_sources'])
            
            # Update config if provided
            if 'config' in data:
                self.config.update(data['config'])
            
            self.logger.info(f"Imported {len(data.get('sources', []))} sources")
            
        except Exception as e:
            raise ValidationError(
                "Failed to import source database",
                validation_type="database_import",
                original_exception=e
            )

    def cleanup_old_data(self, days_old: int = 90) -> None:
        """Clean up old validation data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clean old validation history
                cursor.execute(
                    'DELETE FROM validation_history WHERE timestamp < ?',
                    (cutoff_date.isoformat(),)
                )
                
                # Clean expired cache entries
                cursor.execute(
                    'DELETE FROM cross_reference_cache WHERE expiry_date < ?',
                    (datetime.now().isoformat(),)
                )
                
                conn.commit()
                
                self.logger.info(f"Cleaned up validation data older than {days_old} days")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
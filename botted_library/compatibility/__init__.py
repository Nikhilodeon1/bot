"""
Backward Compatibility Layer for Botted Library v2

This module provides backward compatibility with v1 interfaces while
automatically enabling collaborative features in the background.
"""

from .v1_compatibility import (
    create_worker,
    Worker,
    enable_collaborative_features,
    disable_collaborative_features,
    get_compatibility_status
)

__all__ = [
    'create_worker',
    'Worker', 
    'enable_collaborative_features',
    'disable_collaborative_features',
    'get_compatibility_status'
]
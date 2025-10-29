"""
Helper utilities for the Botted Library

Provides common utility functions for validation, formatting,
file operations, and other general-purpose tasks.
"""

import re
import os
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urlparse, urljoin


def validate_url(url: str) -> bool:
    """
    Validate if a string is a valid URL
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    try:
        if not url or not isinstance(url, str):
            return False
        
        # Basic URL pattern check
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            return False
        
        # Use urllib.parse for additional validation
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
        
    except Exception:
        return False


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename for safe file system operations
    
    Args:
        filename: Original filename
        max_length: Maximum allowed filename length
        
    Returns:
        Sanitized filename safe for file system use
    """
    if not filename or not isinstance(filename, str):
        return "unnamed_file"
    
    # Remove or replace invalid characters
    # Invalid characters for most file systems: < > : " | ? * \ /
    invalid_chars = r'[<>:"|?*\\/]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    
    # Handle reserved names on Windows
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_without_ext = Path(sanitized).stem.upper()
    if name_without_ext in reserved_names:
        sanitized = f"_{sanitized}"
    
    # Truncate if too long, preserving extension
    if len(sanitized) > max_length:
        path_obj = Path(sanitized)
        stem = path_obj.stem
        suffix = path_obj.suffix
        
        # Calculate available space for stem
        available_length = max_length - len(suffix)
        if available_length > 0:
            sanitized = stem[:available_length] + suffix
        else:
            sanitized = stem[:max_length]
    
    # Ensure we have a valid filename
    if not sanitized:
        sanitized = "unnamed_file"
    
    return sanitized


def format_timestamp(timestamp: Optional[datetime] = None, 
                    format_str: str = "%Y-%m-%d %H:%M:%S", 
                    use_utc: bool = False) -> str:
    """
    Format timestamp for consistent display
    
    Args:
        timestamp: Datetime object to format (uses current time if None)
        format_str: Format string for datetime formatting
        use_utc: Whether to use UTC timezone
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc) if use_utc else datetime.now()
    
    if use_utc and timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    
    return timestamp.strftime(format_str)


def generate_unique_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate unique identifier
    
    Args:
        prefix: Optional prefix for the ID
        length: Length of the random part
        
    Returns:
        Unique identifier string
    """
    unique_part = str(uuid.uuid4()).replace('-', '')[:length]
    return f"{prefix}{unique_part}" if prefix else unique_part


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = 'sha256') -> str:
    """
    Calculate hash of file contents
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256, etc.)
        
    Returns:
        Hexadecimal hash string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If algorithm is not supported
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        hash_obj = hashlib.new(algorithm)
    except ValueError:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with fallback
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON object or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: Any = None, **kwargs) -> str:
    """
    Safely serialize object to JSON string
    
    Args:
        obj: Object to serialize
        default: Default serializer function
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        JSON string or empty string if serialization fails
    """
    try:
        return json.dumps(obj, default=default, **kwargs)
    except (TypeError, ValueError):
        return "{}"


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if necessary
    
    Args:
        path: Directory path
        
    Returns:
        Path object for the directory
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get file size in bytes
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    return path.stat().st_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix
    
    Args:
        text: Text to truncate
        max_length: Maximum allowed length
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def clean_text(text: str, remove_extra_whitespace: bool = True, 
               remove_special_chars: bool = False) -> str:
    """
    Clean and normalize text
    
    Args:
        text: Text to clean
        remove_extra_whitespace: Whether to remove extra whitespace
        remove_special_chars: Whether to remove special characters
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    cleaned = text
    
    # Remove extra whitespace
    if remove_extra_whitespace:
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Remove special characters (keep alphanumeric and basic punctuation)
    if remove_special_chars:
        cleaned = re.sub(r'[^\w\s\.\,\!\?\-]', '', cleaned)
    
    return cleaned


def merge_dictionaries(*dicts: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
    """
    Merge multiple dictionaries
    
    Args:
        *dicts: Dictionaries to merge
        deep: Whether to perform deep merge for nested dictionaries
        
    Returns:
        Merged dictionary
    """
    result = {}
    
    for d in dicts:
        if not isinstance(d, dict):
            continue
        
        for key, value in d.items():
            if deep and key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dictionaries(result[key], value, deep=True)
            else:
                result[key] = value
    
    return result


def flatten_dictionary(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flatten nested dictionary using dot notation
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        
        if isinstance(v, dict):
            items.extend(flatten_dictionary(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    
    return dict(items)


def retry_operation(func, max_attempts: int = 3, delay: float = 1.0, 
                   exceptions: tuple = (Exception,)) -> Any:
    """
    Retry operation with exponential backoff
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Function result
        
    Raises:
        Last exception if all attempts fail
    """
    import time
    
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
            continue
    
    raise last_exception


def validate_email(email: str) -> bool:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email format is valid
    """
    if not email or not isinstance(email, str):
        return False
    
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    return bool(email_pattern.match(email))


def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain string or None if invalid URL
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None


def is_safe_path(path: Union[str, Path], base_path: Union[str, Path]) -> bool:
    """
    Check if path is safe (within base directory)
    
    Args:
        path: Path to check
        base_path: Base directory path
        
    Returns:
        True if path is safe (no directory traversal)
    """
    try:
        base = Path(base_path).resolve()
        target = Path(path).resolve()
        
        # Check if target is within base directory
        return str(target).startswith(str(base))
        
    except Exception:
        return False


def get_timestamp_filename(prefix: str = "", extension: str = ".txt") -> str:
    """
    Generate filename with timestamp
    
    Args:
        prefix: Filename prefix
        extension: File extension
        
    Returns:
        Filename with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}{timestamp}{extension}" if prefix else f"{timestamp}{extension}"
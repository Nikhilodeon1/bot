"""
Shared File System for Collaborative Spaces

Provides file sharing capabilities with versioning, locking, and access control
for collaborative worker environments.
"""

import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
import hashlib

from .exceptions import DataValidationError


class FilePermission(Enum):
    """File access permissions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class LockType(Enum):
    """File lock types"""
    READ = "read"
    WRITE = "write"
    EXCLUSIVE = "exclusive"


@dataclass
class FileVersion:
    """Represents a version of a file"""
    version_id: str
    filename: str
    content: str
    content_hash: str
    created_by: str
    created_at: datetime
    size: int
    comment: Optional[str] = None

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate file version data"""
        if not self.version_id or not isinstance(self.version_id, str):
            raise DataValidationError("Version ID must be a non-empty string", 
                                    field_name="version_id", field_value=self.version_id, model_type="FileVersion")
        if not self.filename or not isinstance(self.filename, str):
            raise DataValidationError("Filename must be a non-empty string",
                                    field_name="filename", field_value=self.filename, model_type="FileVersion")
        if not isinstance(self.content, str):
            raise DataValidationError("Content must be a string",
                                    field_name="content", field_value=type(self.content).__name__, model_type="FileVersion")
        if not self.created_by or not isinstance(self.created_by, str):
            raise DataValidationError("Created by must be a non-empty string",
                                    field_name="created_by", field_value=self.created_by, model_type="FileVersion")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        from dataclasses import asdict
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileVersion':
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

    @classmethod
    def create_new(cls, filename: str, content: str, created_by: str, comment: Optional[str] = None) -> 'FileVersion':
        """Create a new file version"""
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return cls(
            version_id=str(uuid.uuid4()),
            filename=filename,
            content=content,
            content_hash=content_hash,
            created_by=created_by,
            created_at=datetime.now(),
            size=len(content.encode('utf-8')),
            comment=comment
        )


@dataclass
class FileLock:
    """Represents a file lock"""
    lock_id: str
    filename: str
    worker_id: str
    lock_type: LockType
    acquired_at: datetime
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if lock has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        from dataclasses import asdict
        data = asdict(self)
        data['lock_type'] = self.lock_type.value
        data['acquired_at'] = self.acquired_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileLock':
        """Create from dictionary"""
        data['lock_type'] = LockType(data['lock_type'])
        data['acquired_at'] = datetime.fromisoformat(data['acquired_at'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


@dataclass
class FileHandle:
    """Handle for file operations"""
    filename: str
    current_version_id: str
    created_by: str
    created_at: datetime
    last_modified_by: str
    last_modified_at: datetime
    permissions: Dict[str, Set[FilePermission]]
    is_locked: bool = False
    lock_info: Optional[FileLock] = None

    def has_permission(self, worker_id: str, permission: FilePermission) -> bool:
        """Check if worker has specific permission"""
        worker_permissions = self.permissions.get(worker_id, set())
        return permission in worker_permissions or FilePermission.ADMIN in worker_permissions

    def grant_permission(self, worker_id: str, permission: FilePermission) -> None:
        """Grant permission to worker"""
        if worker_id not in self.permissions:
            self.permissions[worker_id] = set()
        self.permissions[worker_id].add(permission)

    def revoke_permission(self, worker_id: str, permission: FilePermission) -> None:
        """Revoke permission from worker"""
        if worker_id in self.permissions:
            self.permissions[worker_id].discard(permission)


class SharedFileSystem:
    """
    Shared file system for collaborative spaces with versioning, locking, and permissions.
    
    Provides CRUD operations, version control, file locking mechanisms, and access control
    for collaborative worker environments.
    """

    def __init__(self, space_id: str):
        """Initialize shared file system for a collaborative space"""
        self.space_id = space_id
        self._files: Dict[str, FileHandle] = {}
        self._versions: Dict[str, List[FileVersion]] = {}
        self._locks: Dict[str, FileLock] = {}
        self._lock = threading.RLock()
        self._default_lock_timeout = 300  # 5 minutes default lock timeout

    def create_file(self, worker_id: str, filename: str, content: str, comment: Optional[str] = None) -> FileHandle:
        """Create a new file in the shared file system"""
        with self._lock:
            if filename in self._files:
                raise ValueError(f"File '{filename}' already exists")
            
            if not filename or '/' in filename or '\\' in filename:
                raise ValueError(f"Invalid filename: '{filename}'")
            
            # Create initial version
            initial_version = FileVersion.create_new(filename, content, worker_id, comment)
            
            # Create file handle with default permissions
            now = datetime.now()
            file_handle = FileHandle(
                filename=filename,
                current_version_id=initial_version.version_id,
                created_by=worker_id,
                created_at=now,
                last_modified_by=worker_id,
                last_modified_at=now,
                permissions={worker_id: {FilePermission.READ, FilePermission.WRITE, FilePermission.DELETE, FilePermission.ADMIN}}
            )
            
            # Store file and version
            self._files[filename] = file_handle
            self._versions[filename] = [initial_version]
            
            return file_handle

    def read_file(self, filename: str, worker_id: Optional[str] = None, version_id: Optional[str] = None) -> str:
        """Read file content"""
        with self._lock:
            if filename not in self._files:
                raise FileNotFoundError(f"File '{filename}' not found")
            
            file_handle = self._files[filename]
            
            # Check permissions if worker_id provided
            if worker_id and not file_handle.has_permission(worker_id, FilePermission.READ):
                raise PermissionError(f"Worker '{worker_id}' does not have read permission for '{filename}'")
            
            versions = self._versions[filename]
            
            if version_id:
                # Find specific version
                for version in versions:
                    if version.version_id == version_id:
                        return version.content
                raise ValueError(f"Version '{version_id}' not found for file '{filename}'")
            else:
                # Return current version
                current_version_id = file_handle.current_version_id
                for version in versions:
                    if version.version_id == current_version_id:
                        return version.content
                raise ValueError(f"Current version '{current_version_id}' not found for file '{filename}'")

    def update_file(self, worker_id: str, filename: str, content: str, comment: Optional[str] = None) -> None:
        """Update file content, creating a new version"""
        with self._lock:
            if filename not in self._files:
                raise FileNotFoundError(f"File '{filename}' not found")
            
            file_handle = self._files[filename]
            
            # Check permissions
            if not file_handle.has_permission(worker_id, FilePermission.WRITE):
                raise PermissionError(f"Worker '{worker_id}' does not have write permission for '{filename}'")
            
            # Check if file is locked by another worker
            if file_handle.is_locked and file_handle.lock_info:
                if file_handle.lock_info.worker_id != worker_id:
                    if not file_handle.lock_info.is_expired():
                        raise ValueError(f"File '{filename}' is locked by worker '{file_handle.lock_info.worker_id}'")
                    else:
                        # Lock expired, remove it
                        self._remove_expired_lock(filename)
            
            # Create new version
            new_version = FileVersion.create_new(filename, content, worker_id, comment)
            
            # Update file handle
            file_handle.current_version_id = new_version.version_id
            file_handle.last_modified_by = worker_id
            file_handle.last_modified_at = datetime.now()
            
            # Store new version
            self._versions[filename].append(new_version)

    def delete_file(self, worker_id: str, filename: str) -> None:
        """Delete a file and all its versions"""
        with self._lock:
            if filename not in self._files:
                raise FileNotFoundError(f"File '{filename}' not found")
            
            file_handle = self._files[filename]
            
            # Check permissions
            if not file_handle.has_permission(worker_id, FilePermission.DELETE):
                raise PermissionError(f"Worker '{worker_id}' does not have delete permission for '{filename}'")
            
            # Check if file is locked by another worker
            if file_handle.is_locked and file_handle.lock_info:
                if file_handle.lock_info.worker_id != worker_id:
                    if not file_handle.lock_info.is_expired():
                        raise ValueError(f"File '{filename}' is locked by worker '{file_handle.lock_info.worker_id}'")
            
            # Remove file, versions, and locks
            del self._files[filename]
            del self._versions[filename]
            if filename in self._locks:
                del self._locks[filename]

    def list_files(self, worker_id: Optional[str] = None) -> List[str]:
        """List all files in the shared file system"""
        with self._lock:
            if worker_id is None:
                return list(self._files.keys())
            
            accessible_files = []
            for filename, file_handle in self._files.items():
                if file_handle.has_permission(worker_id, FilePermission.READ):
                    accessible_files.append(filename)
            
            return accessible_files

    def get_file_history(self, filename: str, worker_id: Optional[str] = None) -> List[FileVersion]:
        """Get version history for a file"""
        with self._lock:
            if filename not in self._files:
                raise FileNotFoundError(f"File '{filename}' not found")
            
            file_handle = self._files[filename]
            
            # Check permissions if worker_id provided
            if worker_id and not file_handle.has_permission(worker_id, FilePermission.READ):
                raise PermissionError(f"Worker '{worker_id}' does not have read permission for '{filename}'")
            
            versions = self._versions[filename]
            return sorted(versions, key=lambda v: v.created_at, reverse=True)

    def lock_file(self, worker_id: str, filename: str, lock_type: LockType = LockType.WRITE, 
                  timeout_seconds: Optional[int] = None) -> bool:
        """Acquire a lock on a file"""
        with self._lock:
            if filename not in self._files:
                raise FileNotFoundError(f"File '{filename}' not found")
            
            file_handle = self._files[filename]
            
            # Check permissions based on lock type
            required_permission = FilePermission.READ if lock_type == LockType.READ else FilePermission.WRITE
            if not file_handle.has_permission(worker_id, required_permission):
                raise PermissionError(f"Worker '{worker_id}' does not have {required_permission.value} permission for '{filename}'")
            
            # Check if file is already locked
            if file_handle.is_locked and file_handle.lock_info:
                existing_lock = file_handle.lock_info
                
                # Check if lock expired
                if existing_lock.is_expired():
                    self._remove_expired_lock(filename)
                else:
                    # Check lock compatibility
                    if existing_lock.worker_id == worker_id:
                        # Same worker, allow if compatible lock types
                        if existing_lock.lock_type == LockType.READ and lock_type == LockType.READ:
                            return True
                        return False
                    else:
                        # Different worker, check compatibility
                        if existing_lock.lock_type == LockType.READ and lock_type == LockType.READ:
                            # Multiple read locks allowed
                            pass
                        else:
                            return False
            
            # Create new lock
            timeout = timeout_seconds or self._default_lock_timeout
            expires_at = datetime.now().replace(microsecond=0) + \
                        timedelta(seconds=timeout) if timeout > 0 else None
            
            new_lock = FileLock(
                lock_id=str(uuid.uuid4()),
                filename=filename,
                worker_id=worker_id,
                lock_type=lock_type,
                acquired_at=datetime.now(),
                expires_at=expires_at
            )
            
            # Apply lock
            file_handle.is_locked = True
            file_handle.lock_info = new_lock
            self._locks[filename] = new_lock
            
            return True

    def unlock_file(self, worker_id: str, filename: str) -> None:
        """Release a lock on a file"""
        with self._lock:
            if filename not in self._files:
                raise FileNotFoundError(f"File '{filename}' not found")
            
            file_handle = self._files[filename]
            
            if not file_handle.is_locked or not file_handle.lock_info:
                raise ValueError(f"File '{filename}' is not locked")
            
            if file_handle.lock_info.worker_id != worker_id:
                raise ValueError(f"File '{filename}' is locked by different worker '{file_handle.lock_info.worker_id}'")
            
            # Remove lock
            file_handle.is_locked = False
            file_handle.lock_info = None
            if filename in self._locks:
                del self._locks[filename]

    def grant_permission(self, admin_worker_id: str, filename: str, target_worker_id: str, 
                        permission: FilePermission) -> None:
        """Grant permission to a worker for a file"""
        with self._lock:
            if filename not in self._files:
                raise FileNotFoundError(f"File '{filename}' not found")
            
            file_handle = self._files[filename]
            
            # Check admin permissions
            if not file_handle.has_permission(admin_worker_id, FilePermission.ADMIN):
                raise PermissionError(f"Worker '{admin_worker_id}' does not have admin permission for '{filename}'")
            
            file_handle.grant_permission(target_worker_id, permission)

    def revoke_permission(self, admin_worker_id: str, filename: str, target_worker_id: str, 
                         permission: FilePermission) -> None:
        """Revoke permission from a worker for a file"""
        with self._lock:
            if filename not in self._files:
                raise FileNotFoundError(f"File '{filename}' not found")
            
            file_handle = self._files[filename]
            
            # Check admin permissions
            if not file_handle.has_permission(admin_worker_id, FilePermission.ADMIN):
                raise PermissionError(f"Worker '{admin_worker_id}' does not have admin permission for '{filename}'")
            
            file_handle.revoke_permission(target_worker_id, permission)

    def _remove_expired_lock(self, filename: str) -> None:
        """Remove expired lock from a file"""
        if filename in self._files:
            file_handle = self._files[filename]
            file_handle.is_locked = False
            file_handle.lock_info = None
        
        if filename in self._locks:
            del self._locks[filename]
    
    def get_file_info(self, filename: str, worker_id: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a file"""
        with self._lock:
            if filename not in self._files:
                raise FileNotFoundError(f"File '{filename}' not found")
            
            file_handle = self._files[filename]
            
            if worker_id and not file_handle.has_permission(worker_id, FilePermission.READ):
                raise PermissionError(f"Worker '{worker_id}' does not have read permission for '{filename}'")
            
            versions = self._versions[filename]
            current_version = None
            for version in versions:
                if version.version_id == file_handle.current_version_id:
                    current_version = version
                    break
            
            return {
                'filename': filename,
                'created_by': file_handle.created_by,
                'created_at': file_handle.created_at.isoformat(),
                'last_modified_by': file_handle.last_modified_by,
                'last_modified_at': file_handle.last_modified_at.isoformat(),
                'current_version_id': file_handle.current_version_id,
                'version_count': len(versions),
                'size': current_version.size if current_version else 0,
                'is_locked': file_handle.is_locked,
                'lock_info': file_handle.lock_info.to_dict() if file_handle.lock_info else None,
                'permissions': {
                    worker_id: [perm.value for perm in perms]
                    for worker_id, perms in file_handle.permissions.items()
                } if worker_id and file_handle.has_permission(worker_id, FilePermission.ADMIN) else None
            }

    def cleanup_expired_locks(self) -> int:
        """Clean up expired locks"""
        with self._lock:
            cleaned_count = 0
            expired_files = []
            
            for filename, lock in self._locks.items():
                if lock.is_expired():
                    expired_files.append(filename)
            
            for filename in expired_files:
                self._remove_expired_lock(filename)
                cleaned_count += 1
            
            return cleaned_count

    def get_stats(self) -> Dict[str, Any]:
        """Get file system statistics"""
        with self._lock:
            total_files = len(self._files)
            total_versions = sum(len(versions) for versions in self._versions.values())
            locked_files = sum(1 for file_handle in self._files.values() if file_handle.is_locked)
            total_size = 0
            
            for versions in self._versions.values():
                for version in versions:
                    total_size += version.size
            
            return {
                'space_id': self.space_id,
                'total_files': total_files,
                'total_versions': total_versions,
                'locked_files': locked_files,
                'total_size_bytes': total_size,
                'active_locks': len(self._locks)
            }
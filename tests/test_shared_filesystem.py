"""
Unit tests for SharedFileSystem

Tests file operations, versioning, locking, and permissions in collaborative spaces.
"""

import unittest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from botted_library.core.shared_filesystem import (
    SharedFileSystem, FileVersion, FileLock, FileHandle,
    FilePermission, LockType
)
from botted_library.core.exceptions import DataValidationError


class TestFileVersion(unittest.TestCase):
    """Test cases for FileVersion data model"""
    
    def test_create_new_file_version(self):
        """Test creating a new file version"""
        version = FileVersion.create_new("test.txt", "Hello World", "worker1", "Initial version")
        
        self.assertEqual(version.filename, "test.txt")
        self.assertEqual(version.content, "Hello World")
        self.assertEqual(version.created_by, "worker1")
        self.assertEqual(version.comment, "Initial version")
        self.assertEqual(version.size, len("Hello World".encode('utf-8')))
        self.assertIsNotNone(version.version_id)
        self.assertIsNotNone(version.content_hash)
        self.assertIsInstance(version.created_at, datetime)
    
    def test_file_version_validation(self):
        """Test file version validation"""
        with self.assertRaises(DataValidationError):
            FileVersion("", "test.txt", "content", "hash", "worker1", datetime.now(), 10)
        
        with self.assertRaises(DataValidationError):
            FileVersion("v1", "", "content", "hash", "worker1", datetime.now(), 10)
        
        with self.assertRaises(DataValidationError):
            FileVersion("v1", "test.txt", "content", "hash", "", datetime.now(), 10)
    
    def test_file_version_serialization(self):
        """Test file version serialization and deserialization"""
        version = FileVersion.create_new("test.txt", "Hello World", "worker1")
        
        # Test to_dict and from_dict
        version_dict = version.to_dict()
        restored_version = FileVersion.from_dict(version_dict)
        
        self.assertEqual(version.version_id, restored_version.version_id)
        self.assertEqual(version.filename, restored_version.filename)
        self.assertEqual(version.content, restored_version.content)
        self.assertEqual(version.created_by, restored_version.created_by)


class TestFileLock(unittest.TestCase):
    """Test cases for FileLock data model"""
    
    def test_file_lock_creation(self):
        """Test creating a file lock"""
        lock = FileLock(
            lock_id="lock1",
            filename="test.txt",
            worker_id="worker1",
            lock_type=LockType.WRITE,
            acquired_at=datetime.now()
        )
        
        self.assertEqual(lock.filename, "test.txt")
        self.assertEqual(lock.worker_id, "worker1")
        self.assertEqual(lock.lock_type, LockType.WRITE)
        self.assertFalse(lock.is_expired())
    
    def test_lock_expiration(self):
        """Test lock expiration logic"""
        past_time = datetime.now() - timedelta(minutes=1)
        lock = FileLock(
            lock_id="lock1",
            filename="test.txt",
            worker_id="worker1",
            lock_type=LockType.WRITE,
            acquired_at=past_time,
            expires_at=past_time
        )
        
        self.assertTrue(lock.is_expired())
    
    def test_lock_serialization(self):
        """Test lock serialization and deserialization"""
        lock = FileLock(
            lock_id="lock1",
            filename="test.txt",
            worker_id="worker1",
            lock_type=LockType.WRITE,
            acquired_at=datetime.now()
        )
        
        lock_dict = lock.to_dict()
        restored_lock = FileLock.from_dict(lock_dict)
        
        self.assertEqual(lock.lock_id, restored_lock.lock_id)
        self.assertEqual(lock.filename, restored_lock.filename)
        self.assertEqual(lock.worker_id, restored_lock.worker_id)
        self.assertEqual(lock.lock_type, restored_lock.lock_type)


class TestFileHandle(unittest.TestCase):
    """Test cases for FileHandle data model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.now = datetime.now()
        self.file_handle = FileHandle(
            filename="test.txt",
            current_version_id="v1",
            created_by="worker1",
            created_at=self.now,
            last_modified_by="worker1",
            last_modified_at=self.now,
            permissions={"worker1": {FilePermission.READ, FilePermission.WRITE, FilePermission.ADMIN}}
        )
    
    def test_permission_checking(self):
        """Test permission checking logic"""
        self.assertTrue(self.file_handle.has_permission("worker1", FilePermission.READ))
        self.assertTrue(self.file_handle.has_permission("worker1", FilePermission.WRITE))
        self.assertTrue(self.file_handle.has_permission("worker1", FilePermission.ADMIN))
        self.assertFalse(self.file_handle.has_permission("worker2", FilePermission.READ))
    
    def test_permission_management(self):
        """Test granting and revoking permissions"""
        # Grant permission
        self.file_handle.grant_permission("worker2", FilePermission.READ)
        self.assertTrue(self.file_handle.has_permission("worker2", FilePermission.READ))
        
        # Revoke permission
        self.file_handle.revoke_permission("worker2", FilePermission.READ)
        self.assertFalse(self.file_handle.has_permission("worker2", FilePermission.READ))
    
    def test_admin_permission_override(self):
        """Test that admin permission grants all access"""
        self.file_handle.permissions["worker1"] = {FilePermission.ADMIN}
        
        self.assertTrue(self.file_handle.has_permission("worker1", FilePermission.READ))
        self.assertTrue(self.file_handle.has_permission("worker1", FilePermission.WRITE))
        self.assertTrue(self.file_handle.has_permission("worker1", FilePermission.DELETE))


class TestSharedFileSystem(unittest.TestCase):
    """Test cases for SharedFileSystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fs = SharedFileSystem("space1")
    
    def test_file_system_initialization(self):
        """Test file system initialization"""
        self.assertEqual(self.fs.space_id, "space1")
        self.assertEqual(len(self.fs.list_files()), 0)
    
    def test_create_file(self):
        """Test file creation"""
        file_handle = self.fs.create_file("worker1", "test.txt", "Hello World", "Initial version")
        
        self.assertEqual(file_handle.filename, "test.txt")
        self.assertEqual(file_handle.created_by, "worker1")
        self.assertTrue(file_handle.has_permission("worker1", FilePermission.ADMIN))
        
        # Verify file appears in listing
        files = self.fs.list_files()
        self.assertIn("test.txt", files)
    
    def test_create_duplicate_file(self):
        """Test creating duplicate file raises error"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        
        with self.assertRaises(ValueError):
            self.fs.create_file("worker2", "test.txt", "Duplicate content")
    
    def test_create_file_invalid_name(self):
        """Test creating file with invalid name raises error"""
        with self.assertRaises(ValueError):
            self.fs.create_file("worker1", "test/file.txt", "Content")
        
        with self.assertRaises(ValueError):
            self.fs.create_file("worker1", "", "Content")
    
    def test_read_file(self):
        """Test reading file content"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        
        content = self.fs.read_file("test.txt", "worker1")
        self.assertEqual(content, "Hello World")
    
    def test_read_nonexistent_file(self):
        """Test reading nonexistent file raises error"""
        with self.assertRaises(FileNotFoundError):
            self.fs.read_file("nonexistent.txt", "worker1")
    
    def test_read_file_without_permission(self):
        """Test reading file without permission raises error"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        
        with self.assertRaises(PermissionError):
            self.fs.read_file("test.txt", "worker2")
    
    def test_update_file(self):
        """Test updating file content"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        self.fs.update_file("worker1", "test.txt", "Updated content", "Second version")
        
        content = self.fs.read_file("test.txt", "worker1")
        self.assertEqual(content, "Updated content")
        
        # Check version history
        history = self.fs.get_file_history("test.txt", "worker1")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].content, "Updated content")  # Newest first
        self.assertEqual(history[1].content, "Hello World")
    
    def test_update_file_without_permission(self):
        """Test updating file without permission raises error"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        
        with self.assertRaises(PermissionError):
            self.fs.update_file("worker2", "test.txt", "Unauthorized update")
    
    def test_delete_file(self):
        """Test deleting a file"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        self.fs.delete_file("worker1", "test.txt")
        
        files = self.fs.list_files()
        self.assertNotIn("test.txt", files)
        
        with self.assertRaises(FileNotFoundError):
            self.fs.read_file("test.txt", "worker1")
    
    def test_delete_file_without_permission(self):
        """Test deleting file without permission raises error"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        
        with self.assertRaises(PermissionError):
            self.fs.delete_file("worker2", "test.txt")
    
    def test_file_locking(self):
        """Test file locking mechanism"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        
        # Grant write permission to worker2
        self.fs.grant_permission("worker1", "test.txt", "worker2", FilePermission.WRITE)
        
        # Acquire lock
        success = self.fs.lock_file("worker1", "test.txt", LockType.WRITE)
        self.assertTrue(success)
        
        # Try to acquire lock with different worker
        success = self.fs.lock_file("worker2", "test.txt", LockType.WRITE)
        self.assertFalse(success)
        
        # Release lock
        self.fs.unlock_file("worker1", "test.txt")
        
        # Now other worker can acquire lock
        success = self.fs.lock_file("worker2", "test.txt", LockType.WRITE)
        self.assertTrue(success)
    
    def test_multiple_read_locks(self):
        """Test multiple read locks are allowed"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        self.fs.grant_permission("worker1", "test.txt", "worker2", FilePermission.READ)
        
        # Both workers can acquire read locks
        success1 = self.fs.lock_file("worker1", "test.txt", LockType.READ)
        success2 = self.fs.lock_file("worker2", "test.txt", LockType.READ)
        
        self.assertTrue(success1)
        self.assertTrue(success2)
    
    def test_update_locked_file(self):
        """Test updating a file locked by another worker"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        self.fs.grant_permission("worker1", "test.txt", "worker2", FilePermission.WRITE)
        
        # Worker2 locks the file
        self.fs.lock_file("worker2", "test.txt", LockType.WRITE)
        
        # Worker1 cannot update locked file
        with self.assertRaises(ValueError):
            self.fs.update_file("worker1", "test.txt", "Updated content")
        
        # Worker2 can update their own locked file
        self.fs.update_file("worker2", "test.txt", "Updated by worker2")
        content = self.fs.read_file("test.txt", "worker1")
        self.assertEqual(content, "Updated by worker2")
    
    def test_permission_management(self):
        """Test granting and revoking permissions"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        
        # Grant read permission to worker2
        self.fs.grant_permission("worker1", "test.txt", "worker2", FilePermission.READ)
        
        # Worker2 can now read
        content = self.fs.read_file("test.txt", "worker2")
        self.assertEqual(content, "Hello World")
        
        # Worker2 still cannot write
        with self.assertRaises(PermissionError):
            self.fs.update_file("worker2", "test.txt", "Unauthorized update")
        
        # Revoke permission
        self.fs.revoke_permission("worker1", "test.txt", "worker2", FilePermission.READ)
        
        # Worker2 can no longer read
        with self.assertRaises(PermissionError):
            self.fs.read_file("test.txt", "worker2")
    
    def test_permission_management_without_admin(self):
        """Test permission management without admin rights"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        
        with self.assertRaises(PermissionError):
            self.fs.grant_permission("worker2", "test.txt", "worker3", FilePermission.READ)
    
    def test_file_info(self):
        """Test getting file information"""
        self.fs.create_file("worker1", "test.txt", "Hello World", "Initial version")
        
        info = self.fs.get_file_info("test.txt", "worker1")
        
        self.assertEqual(info['filename'], "test.txt")
        self.assertEqual(info['created_by'], "worker1")
        self.assertEqual(info['version_count'], 1)
        self.assertEqual(info['size'], len("Hello World".encode('utf-8')))
        self.assertFalse(info['is_locked'])
        self.assertIsNotNone(info['permissions'])
    
    def test_file_history(self):
        """Test getting file version history"""
        self.fs.create_file("worker1", "test.txt", "Version 1")
        self.fs.update_file("worker1", "test.txt", "Version 2")
        self.fs.update_file("worker1", "test.txt", "Version 3")
        
        history = self.fs.get_file_history("test.txt", "worker1")
        
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].content, "Version 3")  # Newest first
        self.assertEqual(history[1].content, "Version 2")
        self.assertEqual(history[2].content, "Version 1")
    
    def test_read_specific_version(self):
        """Test reading a specific version of a file"""
        self.fs.create_file("worker1", "test.txt", "Version 1")
        self.fs.update_file("worker1", "test.txt", "Version 2")
        
        history = self.fs.get_file_history("test.txt", "worker1")
        old_version_id = history[1].version_id  # Version 1
        
        content = self.fs.read_file("test.txt", "worker1", old_version_id)
        self.assertEqual(content, "Version 1")
    
    def test_cleanup_expired_locks(self):
        """Test cleaning up expired locks"""
        self.fs.create_file("worker1", "test.txt", "Hello World")
        
        # Acquire lock with very short timeout
        success = self.fs.lock_file("worker1", "test.txt", LockType.WRITE, timeout_seconds=1)
        self.assertTrue(success)
        
        # Wait for lock to expire
        time.sleep(2)
        
        # Clean up expired locks
        cleaned = self.fs.cleanup_expired_locks()
        self.assertEqual(cleaned, 1)
        
        # File should no longer be locked
        info = self.fs.get_file_info("test.txt", "worker1")
        self.assertFalse(info['is_locked'])
    
    def test_file_system_stats(self):
        """Test getting file system statistics"""
        self.fs.create_file("worker1", "file1.txt", "Content 1")
        self.fs.create_file("worker1", "file2.txt", "Content 2")
        self.fs.update_file("worker1", "file1.txt", "Updated content 1")
        
        stats = self.fs.get_stats()
        
        self.assertEqual(stats['space_id'], "space1")
        self.assertEqual(stats['total_files'], 2)
        self.assertEqual(stats['total_versions'], 3)  # 2 initial + 1 update
        self.assertEqual(stats['locked_files'], 0)
        self.assertGreater(stats['total_size_bytes'], 0)
    
    def test_list_files_with_permissions(self):
        """Test listing files with permission filtering"""
        self.fs.create_file("worker1", "public.txt", "Public content")
        self.fs.create_file("worker2", "private.txt", "Private content")
        
        # Worker1 can only see their own file
        worker1_files = self.fs.list_files("worker1")
        self.assertIn("public.txt", worker1_files)
        self.assertNotIn("private.txt", worker1_files)
        
        # Grant permission to worker1 for private file
        self.fs.grant_permission("worker2", "private.txt", "worker1", FilePermission.READ)
        
        # Now worker1 can see both files
        worker1_files = self.fs.list_files("worker1")
        self.assertIn("public.txt", worker1_files)
        self.assertIn("private.txt", worker1_files)


if __name__ == '__main__':
    unittest.main()
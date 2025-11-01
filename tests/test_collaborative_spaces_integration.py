"""
Integration tests for collaborative spaces

Tests multi-worker collaborative space operations, shared whiteboard real-time updates,
file sharing and version control, and resource locking and conflict resolution.
"""

import unittest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from botted_library.core.collaborative_server import CollaborativeServer, ServerConfig
from botted_library.core.collaborative_space import (
    CollaborativeSpace, CollaborativeSpaceManager, ParticipantRole, SpaceState
)
from botted_library.core.shared_whiteboard import (
    SharedWhiteboard, ContentType, Position, Size
)
from botted_library.core.shared_filesystem import (
    SharedFileSystem, FilePermission, LockType
)
from botted_library.core.enhanced_worker import EnhancedWorker, ServerConnection
from botted_library.core.enhanced_worker_registry import WorkerType


class TestCollaborativeSpacesIntegration(unittest.TestCase):
    """Integration tests for collaborative spaces functionality"""
    
    def setUp(self):
        """Set up test fixtures with server and workers"""
        # Create server configuration
        self.server_config = ServerConfig(
            host="localhost",
            port=8766,  # Different port to avoid conflicts
            max_workers=10,
            message_queue_size=100,
            heartbeat_interval=5,
            auto_cleanup=True,
            log_level="DEBUG"
        )
        
        # Create and start collaborative server
        self.server = CollaborativeServer(self.server_config)
        
        # Mock the components to avoid actual network operations
        with patch('botted_library.core.enhanced_worker_registry.EnhancedWorkerRegistry'), \
             patch('botted_library.core.message_router.MessageRouter'):
            self.server.start_server()
        
        # Create mock worker dependencies
        self.mock_memory = Mock()
        self.mock_knowledge = Mock()
        self.mock_browser = Mock()
        self.mock_executor = Mock()
        
        # Create test workers
        self.worker1 = self._create_test_worker("worker1", "Planner Alice", WorkerType.PLANNER)
        self.worker2 = self._create_test_worker("worker2", "Executor Bob", WorkerType.EXECUTOR)
        self.worker3 = self._create_test_worker("worker3", "Verifier Carol", WorkerType.VERIFIER)
        
        # Create collaborative space
        self.space = self.server.create_collaborative_space(
            space_name="Test Collaboration Space",
            created_by="worker1",
            description="Integration test space"
        )
        
        # Setup shared resources
        self.shared_whiteboard = self.space.create_shared_whiteboard("Test Whiteboard")
        
        # Create shared filesystem
        self.shared_files = SharedFileSystem(self.space.space_id)
        self.space.set_shared_files(self.shared_files)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Close collaborative space
        if self.space:
            self.space.close_space()
        
        # Stop server
        if self.server:
            self.server.stop_server()
    
    def _create_test_worker(self, worker_id: str, name: str, worker_type: WorkerType) -> EnhancedWorker:
        """Create a test worker with mocked dependencies"""
        server_connection = ServerConnection(
            server_instance=self.server,
            worker_id=worker_id,
            connection_id=f"conn_{worker_id}",
            connected_at=datetime.now()
        )
        
        worker = EnhancedWorker(
            name=name,
            role=f"Test {worker_type.value}",
            worker_type=worker_type,
            memory_system=self.mock_memory,
            knowledge_validator=self.mock_knowledge,
            browser_controller=self.mock_browser,
            task_executor=self.mock_executor,
            server_connection=server_connection,
            worker_id=worker_id
        )
        
        return worker
    
    def test_multi_worker_space_operations(self):
        """Test multi-worker collaborative space operations"""
        # Note: worker1 is already added as owner when space is created
        # Test adding additional participants
        success2 = self.space.add_participant(
            worker_id="worker2",
            worker_name="Executor Bob",
            worker_type="executor",
            role=ParticipantRole.PARTICIPANT
        )
        self.assertTrue(success2)
        
        success3 = self.space.add_participant(
            worker_id="worker3",
            worker_name="Verifier Carol",
            worker_type="verifier",
            role=ParticipantRole.MODERATOR
        )
        self.assertTrue(success3)
        
        # Verify participants are added (including the original owner)
        participants = self.space.get_participants()
        self.assertEqual(len(participants), 3)
        
        participant_ids = [p.worker_id for p in participants]
        self.assertIn("worker1", participant_ids)
        self.assertIn("worker2", participant_ids)
        self.assertIn("worker3", participant_ids)
        
        # Test message broadcasting
        messages_received = []
        
        def message_handler(message):
            messages_received.append(message)
        
        # Subscribe workers to messages
        self.space.subscribe_to_messages("worker2", message_handler)
        self.space.subscribe_to_messages("worker3", message_handler)
        
        # Broadcast message from worker1
        participants_reached = self.space.broadcast_message(
            sender_id="worker1",
            message_type="task_assignment",
            content={"task": "Analyze requirements", "priority": "high"}
        )
        
        # Should reach 2 participants (excluding sender)
        self.assertEqual(participants_reached, 2)
        
        # Verify messages were received
        time.sleep(0.1)  # Allow time for message delivery
        self.assertEqual(len(messages_received), 2)
        
        # Test direct messaging
        direct_messages = []
        
        def direct_message_handler(message):
            direct_messages.append(message)
        
        self.space.subscribe_to_messages("worker2", direct_message_handler)
        
        success = self.space.send_direct_message(
            sender_id="worker1",
            recipient_id="worker2",
            message_type="task_delegation",
            content={"specific_task": "Implement feature X"}
        )
        self.assertTrue(success)
        
        # Test removing participants
        success = self.space.remove_participant("worker3", "completed tasks")
        self.assertTrue(success)
        
        participants = self.space.get_participants()
        self.assertEqual(len(participants), 2)
    
    def test_shared_whiteboard_real_time_updates(self):
        """Test shared whiteboard real-time updates between workers"""
        # Add participants to space (worker1 already exists as owner)
        self.space.add_participant("worker2", "Bob", "executor", ParticipantRole.PARTICIPANT)
        
        # Track whiteboard changes
        worker1_notifications = []
        worker2_notifications = []
        
        def worker1_change_handler(notification):
            worker1_notifications.append(notification)
        
        def worker2_change_handler(notification):
            worker2_notifications.append(notification)
        
        # Subscribe to whiteboard changes
        self.shared_whiteboard.subscribe_to_changes("worker1", worker1_change_handler)
        self.shared_whiteboard.subscribe_to_changes("worker2", worker2_change_handler)
        
        # Worker1 adds content
        content1 = self.shared_whiteboard.add_content(
            worker_id="worker1",
            content_type=ContentType.TEXT,
            position=Position(x=100, y=100),
            size=Size(width=200, height=50),
            data={"text": "Project Requirements", "font_size": 16}
        )
        self.assertIsNotNone(content1)
        
        # Worker2 adds content
        content2 = self.shared_whiteboard.add_content(
            worker_id="worker2",
            content_type=ContentType.DIAGRAM,
            position=Position(x=300, y=200),
            size=Size(width=150, height=100),
            data={"diagram_type": "flowchart", "nodes": ["Start", "Process", "End"]}
        )
        self.assertIsNotNone(content2)
        
        # Verify real-time notifications
        time.sleep(0.1)  # Allow time for notifications
        
        # Worker1 should receive notifications about both content additions (including their own)
        worker1_content_notifications = [n for n in worker1_notifications if n.get('type') == 'content_added']
        self.assertEqual(len(worker1_content_notifications), 2)
        
        # Worker2 should receive notifications about both content additions (including their own)
        worker2_content_notifications = [n for n in worker2_notifications if n.get('type') == 'content_added']
        self.assertEqual(len(worker2_content_notifications), 2)
        
        # Verify that each worker received notification about the other's content
        worker1_other_notifications = [n for n in worker1_content_notifications if n.get('worker_id') == 'worker2']
        worker2_other_notifications = [n for n in worker2_content_notifications if n.get('worker_id') == 'worker1']
        self.assertEqual(len(worker1_other_notifications), 1)
        self.assertEqual(len(worker2_other_notifications), 1)
        
        # Test content updates
        update_success = self.shared_whiteboard.update_content(
            worker_id="worker1",
            content_id=content1.content_id,
            updates={
                "data": {"text": "Updated Project Requirements", "font_size": 18},
                "style": {"color": "blue"}
            }
        )
        self.assertTrue(update_success)
        
        # Test content locking
        lock_success = self.shared_whiteboard.lock_content("worker1", content1.content_id)
        self.assertTrue(lock_success)
        
        # Worker2 should not be able to update locked content
        update_blocked = self.shared_whiteboard.update_content(
            worker_id="worker2",
            content_id=content1.content_id,
            updates={"data": {"text": "Unauthorized update"}}
        )
        self.assertFalse(update_blocked)
        
        # Unlock content
        unlock_success = self.shared_whiteboard.unlock_content("worker1", content1.content_id)
        self.assertTrue(unlock_success)
        
        # Now worker2 can update
        update_success = self.shared_whiteboard.update_content(
            worker_id="worker2",
            content_id=content1.content_id,
            updates={"data": {"text": "Collaborative update"}}
        )
        self.assertTrue(update_success)
        
        # Verify all content is accessible
        all_content = self.shared_whiteboard.get_all_content()
        self.assertEqual(len(all_content), 2)
    
    def test_file_sharing_and_version_control(self):
        """Test file sharing and version control in collaborative spaces"""
        # Add participants (worker1 already exists as owner)
        self.space.add_participant("worker2", "Bob", "executor", ParticipantRole.PARTICIPANT)
        
        # Worker1 creates a file
        file_handle = self.shared_files.create_file(
            worker_id="worker1",
            filename="project_plan.md",
            content="# Project Plan\n\n## Phase 1\n- Requirements gathering",
            comment="Initial project plan"
        )
        self.assertEqual(file_handle.filename, "project_plan.md")
        self.assertEqual(file_handle.created_by, "worker1")
        
        # Grant read and write permissions to worker2
        self.shared_files.grant_permission(
            admin_worker_id="worker1",
            filename="project_plan.md",
            target_worker_id="worker2",
            permission=FilePermission.READ
        )
        self.shared_files.grant_permission(
            admin_worker_id="worker1",
            filename="project_plan.md",
            target_worker_id="worker2",
            permission=FilePermission.WRITE
        )
        
        # Worker2 can now read the file
        content = self.shared_files.read_file("project_plan.md", "worker2")
        self.assertIn("Requirements gathering", content)
        
        # Worker2 updates the file (creates new version)
        self.shared_files.update_file(
            worker_id="worker2",
            filename="project_plan.md",
            content="# Project Plan\n\n## Phase 1\n- Requirements gathering\n- Analysis\n\n## Phase 2\n- Implementation",
            comment="Added Phase 2"
        )
        
        # Worker1 makes another update
        self.shared_files.update_file(
            worker_id="worker1",
            filename="project_plan.md",
            content="# Project Plan\n\n## Phase 1\n- Requirements gathering\n- Analysis\n- Design\n\n## Phase 2\n- Implementation\n- Testing",
            comment="Added Design and Testing"
        )
        
        # Verify version history
        history = self.shared_files.get_file_history("project_plan.md", "worker1")
        self.assertEqual(len(history), 3)  # Initial + 2 updates
        
        # Verify versions are in correct order (newest first)
        self.assertEqual(history[0].created_by, "worker1")  # Latest update
        self.assertEqual(history[1].created_by, "worker2")  # Middle update
        self.assertEqual(history[2].created_by, "worker1")  # Initial version
        
        # Verify version content
        self.assertIn("Testing", history[0].content)
        self.assertIn("Phase 2", history[1].content)
        self.assertNotIn("Phase 2", history[2].content)
        
        # Test reading specific version
        old_content = self.shared_files.read_file(
            filename="project_plan.md",
            worker_id="worker1",
            version_id=history[2].version_id  # Original version
        )
        self.assertNotIn("Phase 2", old_content)
        self.assertIn("Requirements gathering", old_content)
        
        # Test file information
        file_info = self.shared_files.get_file_info("project_plan.md", "worker1")
        self.assertEqual(file_info['filename'], "project_plan.md")
        self.assertEqual(file_info['version_count'], 3)
        self.assertFalse(file_info['is_locked'])
        
        # Test collaborative file creation
        worker2_file = self.shared_files.create_file(
            worker_id="worker2",
            filename="implementation_notes.txt",
            content="Implementation notes for Phase 2"
        )
        self.assertEqual(worker2_file.created_by, "worker2")
        
        # Worker1 should not be able to read worker2's file without permission
        with self.assertRaises(PermissionError):
            self.shared_files.read_file("implementation_notes.txt", "worker1")
        
        # Grant permission
        self.shared_files.grant_permission(
            admin_worker_id="worker2",
            filename="implementation_notes.txt",
            target_worker_id="worker1",
            permission=FilePermission.READ
        )
        
        # Now worker1 can read
        notes_content = self.shared_files.read_file("implementation_notes.txt", "worker1")
        self.assertIn("Implementation notes", notes_content)
    
    def test_resource_locking_and_conflict_resolution(self):
        """Test resource locking and conflict resolution mechanisms"""
        # Add participants (worker1 already exists as owner)
        self.space.add_participant("worker2", "Bob", "executor", ParticipantRole.PARTICIPANT)
        self.space.add_participant("worker3", "Carol", "verifier", ParticipantRole.PARTICIPANT)
        
        # Create a shared file
        self.shared_files.create_file(
            worker_id="worker1",
            filename="shared_document.txt",
            content="Shared document for collaboration"
        )
        
        # Grant permissions to all workers
        for worker_id in ["worker2", "worker3"]:
            self.shared_files.grant_permission(
                admin_worker_id="worker1",
                filename="shared_document.txt",
                target_worker_id=worker_id,
                permission=FilePermission.READ
            )
            self.shared_files.grant_permission(
                admin_worker_id="worker1",
                filename="shared_document.txt",
                target_worker_id=worker_id,
                permission=FilePermission.WRITE
            )
        
        # Test file locking
        lock_success = self.shared_files.lock_file(
            worker_id="worker1",
            filename="shared_document.txt",
            lock_type=LockType.WRITE
        )
        self.assertTrue(lock_success)
        
        # Worker2 should not be able to acquire write lock
        lock_blocked = self.shared_files.lock_file(
            worker_id="worker2",
            filename="shared_document.txt",
            lock_type=LockType.WRITE
        )
        self.assertFalse(lock_blocked)
        
        # Worker2 should not be able to update locked file
        with self.assertRaises(ValueError):
            self.shared_files.update_file(
                worker_id="worker2",
                filename="shared_document.txt",
                content="Unauthorized update"
            )
        
        # Worker1 can update their own locked file
        self.shared_files.update_file(
            worker_id="worker1",
            filename="shared_document.txt",
            content="Updated by lock owner"
        )
        
        # Release lock
        self.shared_files.unlock_file("worker1", "shared_document.txt")
        
        # Now worker2 can acquire lock and update
        lock_success = self.shared_files.lock_file(
            worker_id="worker2",
            filename="shared_document.txt",
            lock_type=LockType.WRITE
        )
        self.assertTrue(lock_success)
        
        self.shared_files.update_file(
            worker_id="worker2",
            filename="shared_document.txt",
            content="Updated by worker2"
        )
        
        # Test multiple read locks
        self.shared_files.unlock_file("worker2", "shared_document.txt")
        
        read_lock1 = self.shared_files.lock_file(
            worker_id="worker1",
            filename="shared_document.txt",
            lock_type=LockType.READ
        )
        self.assertTrue(read_lock1)
        
        read_lock2 = self.shared_files.lock_file(
            worker_id="worker2",
            filename="shared_document.txt",
            lock_type=LockType.READ
        )
        self.assertTrue(read_lock2)
        
        # Both workers can read
        content1 = self.shared_files.read_file("shared_document.txt", "worker1")
        content2 = self.shared_files.read_file("shared_document.txt", "worker2")
        self.assertEqual(content1, content2)
        
        # Test whiteboard content locking
        whiteboard_content = self.shared_whiteboard.add_content(
            worker_id="worker1",
            content_type=ContentType.NOTE,
            position=Position(x=50, y=50),
            size=Size(width=100, height=100),
            data={"note": "Important note"}
        )
        
        # Lock whiteboard content
        wb_lock_success = self.shared_whiteboard.lock_content("worker1", whiteboard_content.content_id)
        self.assertTrue(wb_lock_success)
        
        # Worker2 cannot update locked content
        wb_update_blocked = self.shared_whiteboard.update_content(
            worker_id="worker2",
            content_id=whiteboard_content.content_id,
            updates={"data": {"note": "Unauthorized change"}}
        )
        self.assertFalse(wb_update_blocked)
        
        # Unlock and allow update
        wb_unlock_success = self.shared_whiteboard.unlock_content("worker1", whiteboard_content.content_id)
        self.assertTrue(wb_unlock_success)
        
        wb_update_success = self.shared_whiteboard.update_content(
            worker_id="worker2",
            content_id=whiteboard_content.content_id,
            updates={"data": {"note": "Collaborative change"}}
        )
        self.assertTrue(wb_update_success)
    
    def test_concurrent_operations(self):
        """Test concurrent operations in collaborative spaces"""
        # Add participants (worker1 already exists as owner)
        self.space.add_participant("worker2", "Bob", "executor", ParticipantRole.PARTICIPANT)
        
        # Create shared file
        self.shared_files.create_file(
            worker_id="worker1",
            filename="concurrent_test.txt",
            content="Initial content"
        )
        
        # Grant permissions
        self.shared_files.grant_permission(
            admin_worker_id="worker1",
            filename="concurrent_test.txt",
            target_worker_id="worker2",
            permission=FilePermission.READ
        )
        self.shared_files.grant_permission(
            admin_worker_id="worker1",
            filename="concurrent_test.txt",
            target_worker_id="worker2",
            permission=FilePermission.WRITE
        )
        
        # Test concurrent file operations
        results = []
        errors = []
        
        def worker1_operations():
            try:
                # Try to lock and update
                if self.shared_files.lock_file("worker1", "concurrent_test.txt", LockType.WRITE):
                    time.sleep(0.1)  # Hold lock briefly
                    self.shared_files.update_file(
                        worker_id="worker1",
                        filename="concurrent_test.txt",
                        content="Updated by worker1"
                    )
                    self.shared_files.unlock_file("worker1", "concurrent_test.txt")
                    results.append("worker1_success")
                else:
                    results.append("worker1_blocked")
            except Exception as e:
                errors.append(f"worker1_error: {e}")
        
        def worker2_operations():
            try:
                time.sleep(0.05)  # Slight delay to create race condition
                # Try to lock and update
                if self.shared_files.lock_file("worker2", "concurrent_test.txt", LockType.WRITE):
                    self.shared_files.update_file(
                        worker_id="worker2",
                        filename="concurrent_test.txt",
                        content="Updated by worker2"
                    )
                    self.shared_files.unlock_file("worker2", "concurrent_test.txt")
                    results.append("worker2_success")
                else:
                    results.append("worker2_blocked")
            except Exception as e:
                errors.append(f"worker2_error: {e}")
        
        # Run concurrent operations
        thread1 = threading.Thread(target=worker1_operations)
        thread2 = threading.Thread(target=worker2_operations)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")
        self.assertEqual(len(results), 2)
        
        # One should succeed, one should be blocked
        self.assertIn("worker1_success", results)
        self.assertIn("worker2_blocked", results)
        
        # Verify final file content
        final_content = self.shared_files.read_file("concurrent_test.txt", "worker1")
        self.assertEqual(final_content, "Updated by worker1")
    
    def test_space_lifecycle_and_cleanup(self):
        """Test collaborative space lifecycle and cleanup operations"""
        # Create additional space for testing
        test_space = self.server.create_collaborative_space(
            space_name="Lifecycle Test Space",
            created_by="worker1",
            description="Testing space lifecycle"
        )
        
        # Add participants (worker1 already exists as owner)
        test_space.add_participant("worker2", "Bob", "executor", ParticipantRole.PARTICIPANT)
        
        # Create resources
        test_whiteboard = test_space.create_shared_whiteboard("Lifecycle Whiteboard")
        test_files = SharedFileSystem(test_space.space_id)
        test_space.set_shared_files(test_files)
        
        # Add content to resources
        test_whiteboard.add_content(
            worker_id="worker1",
            content_type=ContentType.TEXT,
            position=Position(x=0, y=0),
            size=Size(width=100, height=50),
            data={"text": "Test content"}
        )
        
        test_files.create_file(
            worker_id="worker1",
            filename="lifecycle_test.txt",
            content="Test file content"
        )
        
        # Verify space is active
        self.assertEqual(test_space.state, SpaceState.ACTIVE)
        self.assertEqual(len(test_space.get_participants()), 2)
        
        # Test space pause
        test_space.pause_space()
        self.assertEqual(test_space.state, SpaceState.PAUSED)
        
        # Test space resume
        test_space.resume_space()
        self.assertEqual(test_space.state, SpaceState.ACTIVE)
        
        # Test space closure
        test_space.close_space()
        self.assertEqual(test_space.state, SpaceState.CLOSED)
        
        # Verify cleanup
        self.assertEqual(len(test_space.message_subscribers), 0)
        
        # Test space manager statistics
        space_manager = self.server.get_collaborative_space_manager()
        stats = space_manager.get_manager_statistics()
        
        self.assertGreaterEqual(stats['total_spaces_created'], 2)  # Our test spaces
        self.assertIsInstance(stats['active_spaces'], int)
        self.assertIsInstance(stats['total_participants'], int)


if __name__ == '__main__':
    unittest.main()
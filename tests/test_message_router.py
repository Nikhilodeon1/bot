"""
Unit tests for MessageRouter

Tests the message routing system for reliable inter-worker communication
with queuing, delivery confirmation, and message history tracking.
"""

import unittest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from queue import Queue, Empty

from botted_library.core.message_router import (
    MessageRouter, CollaborativeMessage, MessageType, MessagePriority,
    DeliveryStatus, MessageDeliveryRecord
)
from botted_library.core.exceptions import WorkerError


class TestMessageRouter(unittest.TestCase):
    """Test cases for MessageRouter"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock worker registry
        self.mock_registry = Mock()
        self.mock_registry.get_active_workers.return_value = [
            {'worker_id': 'worker_1', 'name': 'Worker1'},
            {'worker_id': 'worker_2', 'name': 'Worker2'}
        ]
        
        self.router = MessageRouter(
            worker_registry=self.mock_registry,
            queue_size=100
        )
    
    def tearDown(self):
        """Clean up after tests"""
        self.router.shutdown()
    
    def test_router_initialization(self):
        """Test message router initialization"""
        self.assertEqual(self.router.worker_registry, self.mock_registry)
        self.assertEqual(self.router.queue_size, 100)
        self.assertIsInstance(self.router.message_queues, dict)
        self.assertIsInstance(self.router.pending_messages, dict)
        self.assertIsInstance(self.router.message_history, list)
        self.assertIsInstance(self.router.delivery_records, list)
        self.assertIsInstance(self.router.routing_stats, dict)
    
    def test_route_message_success(self):
        """Test successful message routing"""
        message_content = {
            'message_type': MessageType.TASK_DELEGATION.value,
            'content': 'Test task delegation',
            'priority': MessagePriority.NORMAL.value
        }
        
        success = self.router.route_message('worker_1', 'worker_2', message_content)
        
        # Verify routing success
        self.assertTrue(success)
        self.assertEqual(self.router.routing_stats['total_messages'], 1)
        self.assertEqual(
            self.router.routing_stats['messages_by_type'][MessageType.TASK_DELEGATION.value], 
            1
        )
        
        # Verify message was queued
        self.assertIn('worker_2', self.router.message_queues)
        self.assertFalse(self.router.message_queues['worker_2'].empty())
    
    def test_route_message_invalid_workers(self):
        """Test message routing with invalid workers"""
        # Mock registry to return empty worker list
        self.mock_registry.get_active_workers.return_value = []
        
        message_content = {'content': 'test message'}
        
        with self.assertRaises(WorkerError) as context:
            self.router.route_message('invalid_1', 'invalid_2', message_content)
        
        self.assertIn("Invalid worker IDs", str(context.exception))
    
    def test_broadcast_message_all_workers(self):
        """Test broadcasting message to all workers"""
        # Mock get_active_workers to handle exclude_worker_id parameter
        def mock_get_active_workers(exclude_worker_id=None):
            all_workers = [
                {'worker_id': 'worker_1', 'name': 'Worker1'},
                {'worker_id': 'worker_2', 'name': 'Worker2'}
            ]
            if exclude_worker_id:
                return [w for w in all_workers if w['worker_id'] != exclude_worker_id]
            return all_workers
        
        self.mock_registry.get_active_workers.side_effect = mock_get_active_workers
        
        message_content = {
            'content': 'Broadcast test message',
            'message_type': MessageType.STATUS_UPDATE.value
        }
        
        sent_count = self.router.broadcast_message('worker_1', message_content)
        
        # Should send to one worker (excluding sender)
        self.assertEqual(sent_count, 1)
        
        # Verify message was queued for worker_2
        self.assertIn('worker_2', self.router.message_queues)
        self.assertFalse(self.router.message_queues['worker_2'].empty())
    
    def test_broadcast_message_specific_types(self):
        """Test broadcasting to specific worker types"""
        # Mock registry to return workers with types AND make them valid in active workers
        self.mock_registry.find_workers_by_type.return_value = [
            {'worker_id': 'executor_1', 'name': 'Executor1'}
        ]
        
        # Also need to mock get_active_workers to include the executor for validation
        self.mock_registry.get_active_workers.return_value = [
            {'worker_id': 'worker_1', 'name': 'Worker1'},
            {'worker_id': 'executor_1', 'name': 'Executor1'}
        ]
        
        message_content = {'content': 'Type-specific broadcast'}
        
        sent_count = self.router.broadcast_message(
            'worker_1', 
            message_content, 
            target_worker_types=['executor']
        )
        
        # Should send to executor workers
        self.assertEqual(sent_count, 1)
    
    def test_subscribe_to_messages(self):
        """Test message subscription"""
        callback = Mock()
        
        subscription_id = self.router.subscribe_to_messages('worker_1', callback)
        
        # Verify subscription
        self.assertIsNotNone(subscription_id)
        self.assertIn('worker_1', self.router.message_subscribers)
        self.assertIn(callback, self.router.message_subscribers['worker_1'])
    
    def test_unsubscribe_from_messages(self):
        """Test message unsubscription"""
        callback = Mock()
        
        # Subscribe first
        self.router.subscribe_to_messages('worker_1', callback)
        
        # Unsubscribe
        success = self.router.unsubscribe_from_messages('worker_1', callback)
        
        # Verify unsubscription
        self.assertTrue(success)
        self.assertNotIn(callback, self.router.message_subscribers.get('worker_1', []))
    
    def test_unsubscribe_nonexistent_callback(self):
        """Test unsubscribing non-existent callback"""
        callback = Mock()
        
        success = self.router.unsubscribe_from_messages('worker_1', callback)
        
        # Should return False for non-existent callback
        self.assertFalse(success)
    
    def test_get_message_history(self):
        """Test getting message history"""
        # Add some messages to history
        message1 = CollaborativeMessage(
            message_id='msg_1',
            from_worker_id='worker_1',
            to_worker_id='worker_2',
            message_type=MessageType.TASK_DELEGATION,
            content={'test': 'message1'}
        )
        
        message2 = CollaborativeMessage(
            message_id='msg_2',
            from_worker_id='worker_2',
            to_worker_id='worker_1',
            message_type=MessageType.RESULT_REPORT,
            content={'test': 'message2'}
        )
        
        self.router.message_history.extend([message1, message2])
        
        # Get history for worker_1
        history = self.router.get_message_history('worker_1', limit=10)
        
        # Should return both messages (worker_1 is involved in both)
        self.assertEqual(len(history), 2)
        
        # Should be sorted by creation time (newest first)
        self.assertEqual(history[0].message_id, 'msg_2')
        self.assertEqual(history[1].message_id, 'msg_1')
    
    def test_get_pending_messages(self):
        """Test getting pending messages"""
        # Route a message to create pending messages
        message_content = {'content': 'pending test'}
        self.router.route_message('worker_1', 'worker_2', message_content)
        
        # Get pending messages
        pending = self.router.get_pending_messages('worker_2')
        
        # Should have one pending message
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].content['content'], 'pending test')
    
    def test_get_pending_messages_empty_queue(self):
        """Test getting pending messages from empty queue"""
        pending = self.router.get_pending_messages('nonexistent_worker')
        
        # Should return empty list
        self.assertEqual(len(pending), 0)
    
    def test_process_pending_messages(self):
        """Test processing pending messages"""
        # Mock message subscribers
        callback = Mock()
        self.router.subscribe_to_messages('worker_2', callback)
        
        # Route a message
        message_content = {'content': 'process test'}
        self.router.route_message('worker_1', 'worker_2', message_content)
        
        # Process pending messages
        processed_count = self.router.process_pending_messages()
        
        # Should process one message
        self.assertEqual(processed_count, 1)
        
        # Callback should have been called
        callback.assert_called_once()
    
    def test_get_routing_statistics(self):
        """Test getting routing statistics"""
        # Route some messages to generate statistics
        message_content = {'content': 'stats test'}
        self.router.route_message('worker_1', 'worker_2', message_content)
        
        stats = self.router.get_routing_statistics()
        
        # Verify statistics structure
        self.assertIn('total_messages', stats)
        self.assertIn('successful_deliveries', stats)
        self.assertIn('failed_deliveries', stats)
        self.assertIn('messages_by_type', stats)
        self.assertIn('messages_by_priority', stats)
        self.assertIn('pending_messages', stats)
        self.assertIn('active_subscriptions', stats)
        
        # Verify values
        self.assertEqual(stats['total_messages'], 1)
    
    def test_message_delivery_with_subscribers(self):
        """Test message delivery to subscribers"""
        callback = Mock()
        self.router.subscribe_to_messages('worker_2', callback)
        
        # Create and deliver message directly
        message = CollaborativeMessage(
            message_id='test_msg',
            from_worker_id='worker_1',
            to_worker_id='worker_2',
            message_type=MessageType.TASK_DELEGATION,
            content={'test': 'delivery'}
        )
        
        success = self.router._deliver_message(message)
        
        # Should succeed
        self.assertTrue(success)
        
        # Callback should be called
        callback.assert_called_once_with(message)
        
        # Message should be in history
        self.assertIn(message, self.router.message_history)
    
    def test_message_delivery_no_subscribers(self):
        """Test message delivery with no subscribers"""
        message = CollaborativeMessage(
            message_id='test_msg',
            from_worker_id='worker_1',
            to_worker_id='worker_2',
            message_type=MessageType.TASK_DELEGATION,
            content={'test': 'no_subscribers'}
        )
        
        success = self.router._deliver_message(message)
        
        # Should still succeed (no subscribers is OK)
        self.assertTrue(success)
    
    def test_message_delivery_expired(self):
        """Test delivery of expired message"""
        # Create expired message
        message = CollaborativeMessage(
            message_id='expired_msg',
            from_worker_id='worker_1',
            to_worker_id='worker_2',
            message_type=MessageType.TASK_DELEGATION,
            content={'test': 'expired'},
            expires_at=datetime.now() - timedelta(seconds=1)
        )
        
        success = self.router._deliver_message(message)
        
        # Should fail due to expiration
        self.assertFalse(success)
        self.assertEqual(message.delivery_status, DeliveryStatus.PENDING)
    
    def test_message_delivery_max_attempts(self):
        """Test message delivery with max attempts exceeded"""
        message = CollaborativeMessage(
            message_id='max_attempts_msg',
            from_worker_id='worker_1',
            to_worker_id='worker_2',
            message_type=MessageType.TASK_DELEGATION,
            content={'test': 'max_attempts'},
            max_delivery_attempts=2
        )
        
        # Set attempts to exceed maximum
        message.delivery_attempts = 3
        
        success = self.router._deliver_message(message)
        
        # Should fail due to max attempts
        self.assertFalse(success)
    
    def test_cleanup_expired_messages(self):
        """Test cleanup of expired messages"""
        # Add expired message to pending
        expired_message = CollaborativeMessage(
            message_id='expired_msg',
            from_worker_id='worker_1',
            to_worker_id='worker_2',
            message_type=MessageType.TASK_DELEGATION,
            content={'test': 'expired'},
            expires_at=datetime.now() - timedelta(seconds=1)
        )
        
        self.router.pending_messages['expired_msg'] = expired_message
        
        # Run cleanup
        self.router._cleanup_expired_messages()
        
        # Message should be removed from pending
        self.assertNotIn('expired_msg', self.router.pending_messages)
        
        # Should have delivery record
        self.assertEqual(len(self.router.delivery_records), 1)
        self.assertFalse(self.router.delivery_records[0].success)
    
    def test_router_shutdown(self):
        """Test router shutdown"""
        # Add some data
        self.router.message_queues['test_worker'] = Queue()
        self.router.pending_messages['test_msg'] = Mock()
        callback = Mock()
        self.router.subscribe_to_messages('worker_1', callback)
        
        # Shutdown
        self.router.shutdown()
        
        # Verify cleanup
        self.assertEqual(len(self.router.message_queues), 0)
        self.assertEqual(len(self.router.pending_messages), 0)
        self.assertEqual(len(self.router.message_subscribers), 0)


class TestCollaborativeMessage(unittest.TestCase):
    """Test cases for CollaborativeMessage dataclass"""
    
    def test_message_creation(self):
        """Test creating a collaborative message"""
        message = CollaborativeMessage(
            message_id='test_msg',
            from_worker_id='worker_1',
            to_worker_id='worker_2',
            message_type=MessageType.TASK_DELEGATION,
            content={'task': 'test task'}
        )
        
        self.assertEqual(message.message_id, 'test_msg')
        self.assertEqual(message.from_worker_id, 'worker_1')
        self.assertEqual(message.to_worker_id, 'worker_2')
        self.assertEqual(message.message_type, MessageType.TASK_DELEGATION)
        self.assertEqual(message.content['task'], 'test task')
        self.assertEqual(message.priority, MessagePriority.NORMAL)
        self.assertFalse(message.requires_response)
        self.assertEqual(message.delivery_status, DeliveryStatus.PENDING)
        self.assertEqual(message.delivery_attempts, 0)
    
    def test_message_with_expiration(self):
        """Test message with expiration time"""
        expires_at = datetime.now() + timedelta(minutes=5)
        
        message = CollaborativeMessage(
            message_id='expiring_msg',
            from_worker_id='worker_1',
            to_worker_id='worker_2',
            message_type=MessageType.STATUS_UPDATE,
            content={'status': 'working'},
            expires_at=expires_at
        )
        
        self.assertEqual(message.expires_at, expires_at)
    
    def test_message_high_priority(self):
        """Test high priority message"""
        message = CollaborativeMessage(
            message_id='urgent_msg',
            from_worker_id='worker_1',
            to_worker_id='worker_2',
            message_type=MessageType.ERROR_NOTIFICATION,
            content={'error': 'critical error'},
            priority=MessagePriority.URGENT,
            requires_response=True
        )
        
        self.assertEqual(message.priority, MessagePriority.URGENT)
        self.assertTrue(message.requires_response)


class TestMessageDeliveryRecord(unittest.TestCase):
    """Test cases for MessageDeliveryRecord dataclass"""
    
    def test_delivery_record_creation(self):
        """Test creating a delivery record"""
        delivered_at = datetime.now()
        
        record = MessageDeliveryRecord(
            message_id='test_msg',
            delivered_at=delivered_at,
            delivery_time_ms=150.5,
            success=True
        )
        
        self.assertEqual(record.message_id, 'test_msg')
        self.assertEqual(record.delivered_at, delivered_at)
        self.assertEqual(record.delivery_time_ms, 150.5)
        self.assertTrue(record.success)
        self.assertIsNone(record.error_message)
    
    def test_delivery_record_with_error(self):
        """Test delivery record with error"""
        record = MessageDeliveryRecord(
            message_id='failed_msg',
            delivered_at=datetime.now(),
            delivery_time_ms=0.0,
            success=False,
            error_message="Delivery failed"
        )
        
        self.assertFalse(record.success)
        self.assertEqual(record.error_message, "Delivery failed")


class TestMessageEnums(unittest.TestCase):
    """Test cases for message-related enums"""
    
    def test_message_type_values(self):
        """Test MessageType enum values"""
        self.assertEqual(MessageType.TASK_DELEGATION.value, "task_delegation")
        self.assertEqual(MessageType.VERIFICATION_REQUEST.value, "verification_request")
        self.assertEqual(MessageType.COLLABORATION_INVITE.value, "collaboration_invite")
        self.assertEqual(MessageType.STATUS_UPDATE.value, "status_update")
        self.assertEqual(MessageType.RESULT_REPORT.value, "result_report")
        self.assertEqual(MessageType.ERROR_NOTIFICATION.value, "error_notification")
        self.assertEqual(MessageType.HEARTBEAT.value, "heartbeat")
        self.assertEqual(MessageType.BROADCAST.value, "broadcast")
    
    def test_message_priority_values(self):
        """Test MessagePriority enum values"""
        self.assertEqual(MessagePriority.LOW.value, 1)
        self.assertEqual(MessagePriority.NORMAL.value, 2)
        self.assertEqual(MessagePriority.HIGH.value, 3)
        self.assertEqual(MessagePriority.URGENT.value, 4)
    
    def test_delivery_status_values(self):
        """Test DeliveryStatus enum values"""
        self.assertEqual(DeliveryStatus.PENDING.value, "pending")
        self.assertEqual(DeliveryStatus.DELIVERED.value, "delivered")
        self.assertEqual(DeliveryStatus.FAILED.value, "failed")
        self.assertEqual(DeliveryStatus.EXPIRED.value, "expired")


class TestMessageRouterIntegration(unittest.TestCase):
    """Integration tests for MessageRouter"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_registry = Mock()
        self.mock_registry.get_active_workers.return_value = [
            {'worker_id': 'planner_1', 'name': 'Planner1'},
            {'worker_id': 'executor_1', 'name': 'Executor1'},
            {'worker_id': 'verifier_1', 'name': 'Verifier1'}
        ]
        
        self.router = MessageRouter(self.mock_registry, queue_size=50)
    
    def tearDown(self):
        """Clean up after tests"""
        self.router.shutdown()
    
    def test_full_message_workflow(self):
        """Test complete message workflow"""
        # Setup subscribers
        planner_callback = Mock()
        executor_callback = Mock()
        verifier_callback = Mock()
        
        self.router.subscribe_to_messages('planner_1', planner_callback)
        self.router.subscribe_to_messages('executor_1', executor_callback)
        self.router.subscribe_to_messages('verifier_1', verifier_callback)
        
        # Planner delegates task to executor
        task_message = {
            'message_type': MessageType.TASK_DELEGATION.value,
            'task_description': 'Implement feature X',
            'priority': MessagePriority.HIGH.value,
            'requires_response': True
        }
        
        success = self.router.route_message('planner_1', 'executor_1', task_message)
        self.assertTrue(success)
        
        # Executor requests verification from verifier
        verification_message = {
            'message_type': MessageType.VERIFICATION_REQUEST.value,
            'output_to_verify': 'Feature X implementation',
            'priority': MessagePriority.NORMAL.value
        }
        
        success = self.router.route_message('executor_1', 'verifier_1', verification_message)
        self.assertTrue(success)
        
        # Verifier reports back to planner
        report_message = {
            'message_type': MessageType.RESULT_REPORT.value,
            'verification_result': 'Approved',
            'quality_score': 0.95
        }
        
        success = self.router.route_message('verifier_1', 'planner_1', report_message)
        self.assertTrue(success)
        
        # Process all messages
        processed = self.router.process_pending_messages()
        self.assertEqual(processed, 3)
        
        # Verify callbacks were called
        executor_callback.assert_called_once()
        verifier_callback.assert_called_once()
        planner_callback.assert_called_once()
        
        # Check statistics
        stats = self.router.get_routing_statistics()
        self.assertEqual(stats['total_messages'], 3)
        self.assertEqual(stats['successful_deliveries'], 3)
        self.assertEqual(stats['failed_deliveries'], 0)
        
        # Check message history
        history = self.router.get_message_history('planner_1')
        self.assertEqual(len(history), 2)  # Planner involved in 2 messages


if __name__ == '__main__':
    unittest.main()
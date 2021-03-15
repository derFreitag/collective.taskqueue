# -*- coding: utf-8 -*-
from collective.taskqueue import taskqueue
from collective.taskqueue.interfaces import ITaskQueue
from collective.taskqueue.testing import process_async_tasks
from collective.taskqueue.testing import TASK_QUEUE_FUNCTIONAL_TESTING
from testfixtures import LogCapture
from zope.component import getUtility
import Queue
import transaction
import unittest


class TestLocalVolatileTaskQueue(unittest.TestCase):

    layer = TASK_QUEUE_FUNCTIONAL_TESTING
    queue = "test-queue"

    @property
    def task_queue(self):
        return getUtility(ITaskQueue, name=self.queue)

    def setUp(self):
        self.request = self.layer['request']
        self.task_queue.queue = Queue.Queue()

    def testEmptyQueue(self):
        self.assertEqual(len(self.task_queue), 0)

    def testAddToQueue(self):
        taskqueue.add("/", queue=self.queue)
        self.assertEqual(len(self.task_queue), 0)

    def testCommitToQueue(self):
        taskqueue.add("/", queue=self.queue)
        self.assertEqual(len(self.task_queue), 0)
        transaction.commit()
        self.assertEqual(len(self.task_queue), 1)
        taskqueue.add("/Plone", queue=self.queue)
        self.assertEqual(len(self.task_queue), 1)
        transaction.commit()
        self.assertEqual(len(self.task_queue), 2)

    def testConsumeFromQueue(self):
        self.assertEqual(len(self.task_queue), 0)
        taskqueue.add("/plone/@@view", queue=self.queue)
        transaction.commit()
        self.assertEqual(len(self.task_queue), 1)

        with LogCapture() as output:
            process_async_tasks(self.request, self.queue)
        messages = [record.getMessage() for record in output.records if record.levelname == 'WARNING']
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            messages[0],
            'Async view /plone/@@view is not callable'
        )

    def testConsume20FromQueue(self):
        self.assertEqual(len(self.task_queue), 0)
        expected_result = []
        warning_message = 'Async view /plone/@@view?param={0:02d} is not callable'
        for i in range(20):
            taskqueue.add("/plone/@@view?param={0:02d}".format(i), queue=self.queue)
            expected_result.append(warning_message.format(i))
        transaction.commit()
        self.assertEqual(len(self.task_queue), 20)

        with LogCapture() as output:
            process_async_tasks(self.request, self.queue)
        messages = [record.getMessage() for record in output.records if record.levelname == 'WARNING']

        self.assertEqual(sorted(messages), expected_result)

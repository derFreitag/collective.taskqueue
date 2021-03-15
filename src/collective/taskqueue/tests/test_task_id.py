# -*- coding: utf-8 -*-
from collective.taskqueue import taskqueue
from collective.taskqueue.interfaces import ITaskQueue
from collective.taskqueue.testing import process_async_tasks
from collective.taskqueue.testing import TASK_QUEUE_FUNCTIONAL_TESTING
from testfixtures import LogCapture
from zope.component import getUtility
import logging
import Queue
import transaction
import unittest


logger = logging.getLogger("collective.taskqueue")


class TestLocalVolatileTaskQueue(unittest.TestCase):

    layer = TASK_QUEUE_FUNCTIONAL_TESTING
    queue = "test-queue"

    @property
    def task_queue(self):
        return getUtility(ITaskQueue, name=self.queue)

    def setUp(self):
        self.request = self.layer['request']
        self.task_queue.queue = Queue.Queue()

    def _testConsumeFromQueue(self):
        self.assertEqual(len(self.task_queue), 0)

    def testTaskId(self):
        self.assertEqual(len(self.task_queue), 0)
        a = taskqueue.add("/plone/@@view", queue=self.queue)
        b = taskqueue.add("/plone/@@view", queue=self.queue)
        expected_results = ['Task {0} finished'.format(a), 'Task {0} finished'.format(b), ]
        transaction.commit()
        self.assertEqual(len(self.task_queue), 2)

        with LogCapture() as output:
            process_async_tasks(self.request, self.queue)
        messages = [record.getMessage() for record in output.records if record.levelname == 'INFO']
        self.assertEqual(sorted(messages), sorted(expected_results))

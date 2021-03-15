# -*- coding: utf-8 -*-
from collective.taskqueue import redisqueue
from collective.taskqueue import taskqueue
from collective.taskqueue.interfaces import ITaskQueue
from plone import api
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing.layers import FunctionalTesting
from plone.app.testing.layers import IntegrationTesting
from zope.component import getSiteManager
from zope.component import getUtility


class LocalTaskQueueLayer(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)

    def __init__(self, queue="test-queue"):
        super(LocalTaskQueueLayer, self).__init__()
        self.queue = queue

    def setUpZope(self, app, configurationContext):
        import collective.taskqueue

        self.loadZCML(package=collective.taskqueue)

        queue = taskqueue.LocalVolatileTaskQueue()
        sm = getSiteManager()
        sm.registerUtility(queue, provided=ITaskQueue, name="test-queue")


TASK_QUEUE_FIXTURE = LocalTaskQueueLayer(queue="test-queue")

TASK_QUEUE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(TASK_QUEUE_FIXTURE,), name="TaskQueue:Integration"
)

TASK_QUEUE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(TASK_QUEUE_FIXTURE,), name="TaskQueue:Functional"
)


class RedisTaskQueueLayer(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)

    def __init__(self, queue="test-queue"):
        super(RedisTaskQueueLayer, self).__init__()
        self.queue = queue

    def setUpZope(self, app, configurationContext):
        import collective.taskqueue

        self.loadZCML(package=collective.taskqueue)

        queue = redisqueue.RedisTaskQueue()
        sm = getSiteManager()
        sm.registerUtility(queue, provided=ITaskQueue, name="test-queue")


REDIS_TASK_QUEUE_FIXTURE = RedisTaskQueueLayer(queue="test-queue")

REDIS_TASK_QUEUE_INTEGRATION_TESTING = IntegrationTesting(
    bases=(REDIS_TASK_QUEUE_FIXTURE,), name="RedisTaskQueue:Integration"
)

REDIS_TASK_QUEUE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(REDIS_TASK_QUEUE_FIXTURE,), name="RedisTaskQueue:Functional"
)


def process_async_tasks(request, queue):
    portal = api.portal.get()
    request.set('queue', queue)
    view = api.content.get_view(context=portal, name='process-async-tasks', request=request)
    task_queue = getUtility(ITaskQueue, name=queue)
    while len(task_queue) > 0:
        view()

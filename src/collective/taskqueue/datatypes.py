# -*- coding: utf-8 -*-
from collective.taskqueue.config import TASK_QUEUE_IDENT
from collective.taskqueue.interfaces import ITaskQueue
from zope.component import provideUtility

import os


class TaskQueueFactory(object):
    def __init__(self, data):
        self.ip = None
        self.port = None
        self.host = None
        self.server_name = TASK_QUEUE_IDENT

        self.queue = data['queue']
        self.type = data['type']
        self.kwargs = {
            "host": data['host'],
            "port": data['port'],
            "db": data['db'],
            "password": data['password'],
            "unix_socket_path": data['unix_socket_path'],
        }

        # Drop empty or conflicting kwargs
        for key in [k for k in self.kwargs if self.kwargs[k] in ("", None)]:
            self.kwargs.pop(key)
        if self.kwargs.get("unix_socket_path"):
            self.kwargs.pop("host")
            self.kwargs.pop("port")

    def prepare(self, *args, **kwargs):
        return

    def servertype(self):
        return self.server_name

    def create(self):
        if self.type == 'redis':
            from collective.taskqueue import redis as klass
        elif self.type == 'local':
            from collective.taskqueue import local as klass
        else:
            # support custom task queues
            mod = __import__(
                self.type[: self.type.rfind(".")],
                fromlist=[self.type[self.type.rfind(".") + 1 :]],
            )
            klass = getattr(mod, self.type[self.type.rfind(".") + 1 :])
        task_queue = klass(**self.kwargs)
        provideUtility(task_queue, ITaskQueue, name=self.queue)

        # Support plone.app.debugtoolbar:
        task_queue.ip = self.ip
        task_queue.port = self.port
        task_queue.server_name = "%s:%s" % (self.server_name, self.queue)

        return task_queue


def create_taskqueue():
    data = {
        'queue': os.environ.get('TASKQUEUE_QUEUE', 'default'),
        'type': os.environ.get('TASKQUEUE_TYPE', 'local'),
        'host':  os.environ.get('TASKQUEUE_HOST', 'localhost'),
        'port':  int(os.environ.get('TASKQUEUE_PORT', 6379)),
        'db':  int(os.environ.get('TASKQUEUE_DB', 0)),
        'password':  os.environ.get('TASKQUEUE_PASSWORD', ''),
        'unix_socket_path':  os.environ.get('TASKQUEUE_SOCKET', ''),
    }
    taskqueue = TaskQueueFactory(data)
    taskqueue.create()

# -*- coding: utf-8 -*-
from collective.taskqueue.config import TASK_QUEUE_IDENT
from collective.taskqueue.interfaces import ITaskQueue
from zope.component import provideUtility


class TaskQueueFactory(object):
    def __init__(self, section):
        self.ip = None
        self.port = None
        self.host = None
        self.server_name = TASK_QUEUE_IDENT

        self.queue = section.queue
        self.type = section.type
        self.kwargs = {
            "host": section.host,
            "port": section.port,
            "db": section.db,
            "password": section.password,
            "unix_socket_path": section.unix_socket_path,
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

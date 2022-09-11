# -*- coding: utf-8 -*-
from collective.taskqueue.interfaces import ITaskQueue
from collective.taskqueue.interfaces import ITaskQueueLayer
from plone import api
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.publisher.browser import BrowserView
import logging


logger = logging.getLogger("collective.taskqueue")


class ProcessTaskView(BrowserView):
    """BrowserView to trigger async tasks.

    This view consumes one async task (if any).
    """

    @property
    def name(self):
        """Private key for processing work.

        Should be unique per server, otherwise it could clash.
        """
        return 'instance'

    @property
    def queue(self):
        """General key where to look for tasks queued."""
        return self.request.get('queue', 'default')

    def __call__(self):
        task = self.get_next_task()
        if task:
            self.process_task(task)
            self._mark_as_done(task)
            self._log_task_done(task)
            self.request.response.setStatus(200, lock=True)
            return
        self.request.response.setStatus(204)

    def get_next_task(self):
        task_queue = self._task_queue()
        task = task_queue.get(consumer_name=self.name)
        return task

    def _task_queue(self):
        task_queue = getUtility(ITaskQueue, name=self.queue)
        return task_queue

    def process_task(self, task):
        full_url = task[b'url'].decode()
        path, params = self._split_url(full_url)
        self._prepare_request(params)
        self._call_async_view(path, full_url)

    @staticmethod
    def _split_url(url):
        """Get the plone path and the query string parameters."""
        try:
            path, params = url.split('?')
            return path, params
        except ValueError:
            return url, None

    def _call_async_view(self, path, full_url):
        """Call the queued view."""
        portal = api.portal.get()
        alsoProvides(self.request, ITaskQueueLayer)
        try:
            view = portal.restrictedTraverse(path)
        except KeyError:
            logger.error('Queued async view could not be found: %s', path)
            return

        klass = type(view)
        try:
            parent = view.__parent__
        except AttributeError:
            parent = view
        async_view = klass(parent, self.request)
        try:
            async_view()
        except TypeError:
            logger.warning('Async view %s is not callable', full_url)

    def _prepare_request(self, params):
        """Add the parameters set on the queued request to the current request."""
        if params:
            for argument in params.split('&'):
                key, value = argument.split('=')
                self.request.set(key, value)

    def _mark_as_done(self, task):
        task_queue = self._task_queue()
        task_queue.task_done(task, 'HTTP/1.1 200', self.name, 0)

    @staticmethod
    def _log_task_done(task):
        """Each task has an id stored on the task headers.

        It looks like this:
        ['X-Task-Id: b00f33d5-0190-4bc6-8795-447ea4e56a67', 'X-Task-User-Id: xxx']
        """
        for header in task[b'headers']:
            header = header.encode()
            if 'X-Task-Id' in header:
                _, task_id = header.split(' ')
                break
        else:
            task_id = 'no-task-id-found'

        logger.info('Task %s finished', task_id)

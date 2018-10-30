# -*- coding: utf-8 -*-
from App.config import getConfiguration

import msgpack

from plone.memoize import forever
from zope.interface import implements
import redis

from collective.taskqueue.interfaces import ITaskQueue
from collective.taskqueue.taskqueue import TaskQueueBase
from collective.taskqueue.taskqueue import TaskQueueTransactionDataManager

import hashlib
import logging


logger = logging.getLogger('redisqueue')


class RedisTaskQueueTDM(TaskQueueTransactionDataManager):

    def tpc_vote(self, t):
        # Vote 'no' by raising ConnectionError if Redis is down:
        self.queue.redis.ping()


class RedisTaskQueue(TaskQueueBase):

    implements(ITaskQueue)

    transaction_data_manager = RedisTaskQueueTDM

    def __init__(self, **kwargs):
        self.redis = redis.StrictRedis(**kwargs)
        self.pubsub = self.redis.pubsub()  # Create pubsub for notifications
        self._requeued_processing = False  # Requeue old processing on start

        if getattr(getConfiguration(), 'debug_mode', False):
            self.redis.ping()  # Ensure Zope startup to crash when Redis down

    @property
    @forever.memoize
    def redis_key(self):
        return 'collective.taskqueue.{0:s}'.format(self.name)

    def __len__(self):
        try:
            return int(self.redis.llen(self.redis_key))
        except redis.ConnectionError:
            return 0

    def serialize(self, task):
        return msgpack.dumps(sorted(task.items()))

    def deserialize(self, msg):
        if msg is not None:
            return dict(msgpack.loads(msg))
        else:
            return None

    def put(self, task):
        self.redis.lpush(self.redis_key, self.serialize(task))
        self.redis.publish(self.redis_key, 'lpush')  # Send event

    def get(self, consumer_name):
        consumer_key = '{0:s}.{1:s}'.format(self.redis_key, consumer_name)

        if not self._requeued_processing:
            self._requeue_processing(consumer_name)
        try:
            msg = self.get_next_k4_task(consumer_key)
        except redis.ConnectionError:
            msg = None
        return self.deserialize(msg)

    def task_done(self, task, status_line, consumer_name, consumer_length):
        consumer_key = '{0:s}.{1:s}'.format(self.redis_key, consumer_name)

        self.redis.lrem(consumer_key, -1, self.serialize(task))
        if consumer_length == 0 and int(self.redis.llen(consumer_key)):
            self._requeue_processing(consumer_name)

    def _requeue_processing(self, consumer_name):
        consumer_key = '{0:s}.{1:s}'.format(self.redis_key, consumer_name)

        try:
            while self.redis.llen(consumer_key) > 0:
                self.redis.rpoplpush(consumer_key, self.redis_key)
            self.redis.publish(self.redis_key, 'rpoplpush')  # Send event
            self._requeued_processing = True
        except redis.ConnectionError:
            pass

    def reset(self):
        for key in self.redis.keys(self.redis_key + '*'):
            self.redis.ltrim(key, 1, 0)

    def get_next_k4_task(self, consumer_key):
        loop = True
        loop_count = 0
        hash_first_msg, _ = self._next_in_queue(first=True)

        if not hash_first_msg:
            return

        while loop and loop_count < 50:
            md5_next_msg, next_msg = self._next_in_queue()

            if next_msg and hash_first_msg == md5_next_msg or self._k4_in_payload(next_msg):
                loop = False
                continue

            self.redis.rpoplpush(self.redis_key, self.redis_key)
            loop_count += 1

        if loop_count == 50:
            self._warn_too_much_looping()

        return self.redis.rpoplpush(self.redis_key, consumer_key)

    def _next_in_queue(self, first=False):
        if first:
            msg = self.redis.rpoplpush(self.redis_key, self.redis_key)
        else:
            msg = self.redis.lindex(self.redis_key, -1)

        if msg:
            hex_digest = hashlib.md5(msg).hexdigest()
            return hex_digest, msg

        return None, None

    def _k4_in_payload(self, msg):
        unpacked_data = self.deserialize(msg)
        url = unpacked_data['url']
        return '/@@k4-postprocess' in url

    def _warn_too_much_looping(self):
        length = self.redis.llen(self.redis_key)
        logger.warning(
            ' '.join([
                'Could not loop through the queue. ',
                'Either the queue is too large ({0}) '.format(length),
                'or something happened',
            ])
        )

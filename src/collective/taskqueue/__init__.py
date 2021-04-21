# -*- coding: utf-8 -*-
from collective.taskqueue.taskqueue import LocalVolatileTaskQueue as local
from collective.taskqueue.redisqueue import RedisTaskQueue as redis

from collective.taskqueue.datatypes import create_taskqueue

create_taskqueue()

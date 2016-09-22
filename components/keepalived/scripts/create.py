#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


KEEPALIVED_SERVICE_NAME = 'keepalived'
ctx_properties = utils.ctx_factory.create(KEEPALIVED_SERVICE_NAME)


utils.yum_install('keepalived', KEEPALIVED_SERVICE_NAME)

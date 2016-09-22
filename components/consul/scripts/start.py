#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONSUL_SERVICE_NAME = 'consul'

utils.start_service(CONSUL_SERVICE_NAME)
utils.systemd.enable(CONSUL_SERVICE_NAME)
utils.systemd.verify_alive(CONSUL_SERVICE_NAME)

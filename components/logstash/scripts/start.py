#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties
SERVICE_NAME = runtime_props['service_name']

ctx.logger.info('Starting Logstash Service...')
utils.start_service(SERVICE_NAME, append_prefix=False)

utils.systemd.verify_alive(SERVICE_NAME, append_prefix=False)

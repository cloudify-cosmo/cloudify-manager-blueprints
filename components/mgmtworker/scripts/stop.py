#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties
SERVICE_NAME = runtime_props.get('service_name')


# This makes sure that the `create` script already ran
if SERVICE_NAME:
    ctx.logger.info('Stopping Management Worker Service...')
    utils.systemd.stop(SERVICE_NAME)

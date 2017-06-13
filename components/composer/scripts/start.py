#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties


if 'skip_installation' not in runtime_props:
    ctx.logger.info('Starting Composer (UI) Service...')
    utils.start_service(runtime_props['service_name'])

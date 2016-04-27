#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

RIEMANN_SERVICE_NAME = 'riemann'


ctx.logger.info('Starting Riemann Service...')
utils.start_service_and_archive_properties(RIEMANN_SERVICE_NAME)

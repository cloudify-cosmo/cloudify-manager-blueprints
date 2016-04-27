#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

REST_SERVICE_NAME = 'restservice'


ctx.logger.info('Starting Cloudify REST Service...')
utils.start_service_and_archive_properties(REST_SERVICE_NAME)

#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA
NGINX_SERVICE_NAME = 'nginx'


ctx.logger.info('Starting Nginx Service...')
utils.start_service_and_archive_properties(NGINX_SERVICE_NAME,
                                           append_prefix=False)

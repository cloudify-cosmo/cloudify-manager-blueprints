#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


ctx.logger.info('Removing manager resources')
for path in ['/opt/cloudify',
             '/etc/cloudify',
             '/var/log/cloudify',
             join(utils.get_exec_tempdir(), 'cloudify-ctx')]:
    utils.remove(path)

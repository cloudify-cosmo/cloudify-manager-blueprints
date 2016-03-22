#!/usr/bin/env python

import tempfile
import os
from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


def preconfigure_restservice():

    rest_service_home = '/opt/manager'

    ctx.logger.info('Deploying REST Security configuration file...')
    sec_config = str(ctx.target.node.properties['security'])
    ctx.logger.info('security config: {0}'.format(sec_config))
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        f.write(sec_config)
    utils.move(path, os.path.join(rest_service_home, 'rest-security.conf'))

    utils.systemd.configure('restservice')


preconfigure_restservice()

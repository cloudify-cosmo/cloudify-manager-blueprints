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
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        f.write(ctx.target.node.properties['security'])
    utils.move(path, os.path.join(rest_service_home, 'rest-security.conf'))

    utils.systemd.configure('restservice')


preconfigure_restservice()

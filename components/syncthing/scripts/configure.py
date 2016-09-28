#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


SYNCTHING_SERVICE_NAME = 'syncthing'
ctx_properties = utils.ctx_factory.get(SYNCTHING_SERVICE_NAME)

utils.systemd.configure(SYNCTHING_SERVICE_NAME)
utils.systemd.systemctl('daemon-reload')

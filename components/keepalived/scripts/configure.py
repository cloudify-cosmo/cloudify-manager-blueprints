#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


KEEPALIVED_SERVICE_NAME = 'keepalived'
ctx_properties = utils.ctx_factory.get(KEEPALIVED_SERVICE_NAME)

utils.systemd.configure(KEEPALIVED_SERVICE_NAME)
utils.systemd.systemctl('daemon-reload')

utils.deploy_blueprint_resource(
    'components/keepalived/config/keepalived.conf.tmpl',
    '/etc/keepalived/keepalived.conf',
    KEEPALIVED_SERVICE_NAME
)

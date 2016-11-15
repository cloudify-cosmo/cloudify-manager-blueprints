#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


KEEPALIVED_SERVICE_NAME = 'keepalived'
ctx_properties = utils.ctx_factory.create(KEEPALIVED_SERVICE_NAME)


def install_keepalived():
    keepalived_rpm_url = ctx_properties['keepalived_rpm_url']
    utils.yum_install(keepalived_rpm_url,
                      service_name=KEEPALIVED_SERVICE_NAME)


install_keepalived()

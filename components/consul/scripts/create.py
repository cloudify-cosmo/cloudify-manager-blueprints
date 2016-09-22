#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONSUL_SERVICE_NAME = 'consul'
ctx_properties = utils.ctx_factory.create(CONSUL_SERVICE_NAME)


def install_consul():
    utils.yum_install('unzip', CONSUL_SERVICE_NAME)
    consul_package = \
        utils.download_cloudify_resource(ctx_properties['consul_package_url'],
                                         CONSUL_SERVICE_NAME)
    utils.sudo(['unzip', '-o', consul_package, '-d', '/opt/cloudify/consul'])
    utils.mkdir('/etc/consul.d')


install_consul()

#!/usr/bin/env python

import tempfile
import zipfile

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONSUL_SERVICE_NAME = 'consul'
ctx_properties = utils.ctx_factory.create(CONSUL_SERVICE_NAME)


def install_consul():
    consul_binary = '/opt/consul/consul'
    consul_config_dir = '/etc/consul.d'

    utils.mkdir(dirname(consul_binary))
    utils.mkdir(consul_config_dir)

    consul_package = \
        utils.download_cloudify_resource(ctx_properties['consul_package_url'],
                                         CONSUL_SERVICE_NAME)

    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(consul_package) as consul_archive:
            consul_archive.extractall(temp_dir)

        utils.move(join(temp_dir, 'consul'), consul_binary)
        utils.chmod('+x', consul_binary)
    finally:
        utils.remove(temp_dir)


install_consul()

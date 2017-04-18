#!/usr/bin/env python

import tempfile
import zipfile

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'consul'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME
HOME_DIR = join('/opt', SERVICE_NAME)
CONFIG_DIR = '/etc/consul.d'
runtime_props['files_to_remove'] = [HOME_DIR, CONFIG_DIR]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)


def install_consul():
    consul_binary = join(HOME_DIR, 'consul')

    utils.mkdir(dirname(consul_binary))
    utils.mkdir(CONFIG_DIR)

    consul_package = \
        utils.download_cloudify_resource(ctx_properties['consul_package_url'],
                                         SERVICE_NAME)

    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(consul_package) as consul_archive:
            consul_archive.extractall(temp_dir)

        utils.move(join(temp_dir, 'consul'), consul_binary)
        utils.chmod('+x', consul_binary)
    finally:
        utils.remove(temp_dir)


install_consul()

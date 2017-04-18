#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'syncthing'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME
HOME_DIR = join('/opt', SERVICE_NAME)
runtime_props['files_to_remove'] = [HOME_DIR]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)


def install_syncthing():
    syncthing_package = \
        utils.download_cloudify_resource(
            ctx_properties['syncthing_package_url'],
            SERVICE_NAME
        )
    utils.mkdir(HOME_DIR)
    utils.untar(syncthing_package, destination=HOME_DIR)
    utils.remove(syncthing_package)


install_syncthing()

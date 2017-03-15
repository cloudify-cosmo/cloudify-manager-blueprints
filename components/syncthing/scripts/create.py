#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SYNCTHING_DIRECTORY = '/opt/syncthing'
SYNCTHING_SERVICE_NAME = 'syncthing'
ctx_properties = utils.ctx_factory.create(SYNCTHING_SERVICE_NAME)


def install_syncthing():
    syncthing_package = \
        utils.download_cloudify_resource(
            ctx_properties['syncthing_package_url'], SYNCTHING_SERVICE_NAME)
    utils.mkdir(SYNCTHING_DIRECTORY)
    utils.untar(syncthing_package, destination=SYNCTHING_DIRECTORY)


install_syncthing()

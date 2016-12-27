#!/usr/bin/env python

import os
from os.path import join, dirname
import tempfile

from cloudify import ctx


ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


MANAGER_IP_SETTER_SERVICE_NAME = 'manager-ip-setter'
ctx_properties = utils.ctx_factory.create(MANAGER_IP_SETTER_SERVICE_NAME)

MANAGER_IP_SETTER_SCRIPT_NAME = 'manager-ip-setter.sh'
MANAGER_IP_SETTER_SCRIPT_PATH = join(
    '/opt/cloudify/manager-ip-setter', MANAGER_IP_SETTER_SCRIPT_NAME)


def install_manager_ip_setter():
    utils.mkdir(dirname(MANAGER_IP_SETTER_SCRIPT_PATH))
    config_file_temp_destination = join(tempfile.gettempdir(),
                                        MANAGER_IP_SETTER_SCRIPT_NAME)
    ctx.download_resource_and_render(
        join('components',
             'manager-ip-setter',
             'scripts',
             MANAGER_IP_SETTER_SCRIPT_NAME),
        config_file_temp_destination)
    utils.move(config_file_temp_destination, MANAGER_IP_SETTER_SCRIPT_PATH)
    utils.chmod('+x', MANAGER_IP_SETTER_SCRIPT_PATH)
    utils.systemd.configure(MANAGER_IP_SETTER_SERVICE_NAME)


if os.environ.get('set_manager_ip_on_boot').lower() == 'true':
    install_manager_ip_setter()
else:
    ctx.logger.info('Set manager ip on boot is disabled.')

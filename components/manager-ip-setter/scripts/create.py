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
UPDATE_PROVIDER_CONTEXT_SCRIPT_NAME = 'update-provider-context.py'

MANAGER_IP_SETTER_DIR = '/opt/cloudify/manager-ip-setter'


def deploy_script(script_name):
    config_file_temp_destination = join(tempfile.gettempdir(), script_name)
    ctx.download_resource_and_render(
        join('components', 'manager-ip-setter', 'scripts', script_name),
        config_file_temp_destination)
    remote_script_path = join(MANAGER_IP_SETTER_DIR, script_name)
    utils.move(config_file_temp_destination, remote_script_path)
    utils.chmod('+x', remote_script_path)
    utils.systemd.configure(MANAGER_IP_SETTER_SERVICE_NAME)


def install_manager_ip_setter():
    utils.mkdir(dirname(MANAGER_IP_SETTER_DIR))
    deploy_script(MANAGER_IP_SETTER_SCRIPT_NAME)
    deploy_script(UPDATE_PROVIDER_CONTEXT_SCRIPT_NAME)


if os.environ.get('set_manager_ip_on_boot').lower() == 'true':
    install_manager_ip_setter()
else:
    ctx.logger.info('Set manager ip on boot is disabled.')

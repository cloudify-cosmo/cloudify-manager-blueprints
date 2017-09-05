#!/usr/bin/env python

import os
from os.path import join, dirname
import tempfile

from cloudify import ctx


ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


SERVICE_NAME = 'manager-ip-setter'
runtime_props = ctx.instance.runtime_properties
ctx_properties = ctx.node.properties.get_all()

MANAGER_IP_SETTER_DIR = join('/opt/cloudify', SERVICE_NAME)

runtime_props['files_to_remove'] = [MANAGER_IP_SETTER_DIR]
runtime_props['service_name'] = SERVICE_NAME


def deploy_utils():
    temp_destination = join(tempfile.gettempdir(), 'utils.py')
    ctx.download_resource_and_render(
        join('components', 'utils.py'),
        temp_destination,
    )
    utils_path = join(MANAGER_IP_SETTER_DIR, 'utils.py')
    utils.move(temp_destination, utils_path)

    utils.chmod('550', utils_path)
    utils.chown('root', utils.CLOUDIFY_GROUP, utils_path)


def deploy_sudo_scripts():
    scripts_to_deploy = {
        'manager-ip-setter.sh': 'Run manager IP setter script',
        'update-provider-context.py': 'Run update provider context script',
        'create-internal-ssl-certs.py':
            'Run the scripts that recreates internal SSL certs'
    }

    for script, description in scripts_to_deploy.items():
        utils.deploy_sudo_command_script(script, description, SERVICE_NAME)


def install_manager_ip_setter():
    utils.mkdir(MANAGER_IP_SETTER_DIR)
    utils.set_service_as_cloudify_service(runtime_props)
    deploy_utils()
    deploy_sudo_scripts()
    utils.systemd.configure(SERVICE_NAME)


# Always create the cloudify user, but only install the scripts if flag is true
if os.environ.get('set_manager_ip_on_boot').lower() == 'true':
    install_manager_ip_setter()
else:
    ctx.logger.info('Set manager ip on boot is disabled.')

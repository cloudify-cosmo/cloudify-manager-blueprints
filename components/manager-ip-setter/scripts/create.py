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
runtime_props = ctx.instance.runtime_properties
ctx_properties = utils.ctx_factory.create(MANAGER_IP_SETTER_SERVICE_NAME)

MANAGER_IP_SETTER_USER = ctx_properties['os_user']
MANAGER_IP_SETTER_GROUP = ctx_properties['os_group']
HOMEDIR = ctx_properties['os_homedir']
SUDOERS_INCLUDE_DIR = ctx_properties['sudoers_include_dir']

MANAGER_IP_SETTER_SCRIPT_NAME = 'manager-ip-setter.sh'
UPDATE_PROVIDER_CONTEXT_SCRIPT_NAME = 'update-provider-context.py'
CREATE_INTERNAL_SSL_CERTS_SCRIPT_NAME = 'create-internal-ssl-certs.py'
MANAGER_IP_SETTER_DIR = '/opt/cloudify/manager-ip-setter'

runtime_props['files_to_remove'] = [MANAGER_IP_SETTER_DIR]
runtime_props['service_name'] = MANAGER_IP_SETTER_SERVICE_NAME
runtime_props['service_user'] = MANAGER_IP_SETTER_USER
runtime_props['service_group'] = MANAGER_IP_SETTER_GROUP


def deploy_script(script_name, description):
    config_file_temp_destination = join(tempfile.gettempdir(), script_name)
    ctx.download_resource_and_render(
        join('components', 'manager-ip-setter', 'scripts', script_name),
        config_file_temp_destination)
    remote_script_path = join(MANAGER_IP_SETTER_DIR, script_name)
    utils.move(config_file_temp_destination, remote_script_path)

    utils.chmod('550', remote_script_path)
    utils.chown('root', MANAGER_IP_SETTER_GROUP, remote_script_path)
    utils.allow_user_to_sudo_command(
        runtime_props,
        user=MANAGER_IP_SETTER_USER,
        full_command=remote_script_path,
        description=description,
        sudoers_include_dir=SUDOERS_INCLUDE_DIR,
    )
    utils.systemd.configure(MANAGER_IP_SETTER_SERVICE_NAME)


def deploy_utils():
    temp_destination = join(tempfile.gettempdir(), 'utils.py')
    ctx.download_resource_and_render(
        join('components', 'utils.py'),
        temp_destination,
    )
    utils_path = join(MANAGER_IP_SETTER_DIR, 'utils.py')
    utils.move(temp_destination, utils_path)

    utils.chmod('550', utils_path)
    utils.chown('root', MANAGER_IP_SETTER_GROUP, utils_path)


def install_manager_ip_setter():
    utils.create_service_user(
        user=MANAGER_IP_SETTER_USER,
        home=HOMEDIR,
        group=MANAGER_IP_SETTER_GROUP,
    )
    utils.mkdir(dirname(MANAGER_IP_SETTER_DIR))
    deploy_utils()
    deploy_script(MANAGER_IP_SETTER_SCRIPT_NAME, 'ip_setter')
    deploy_script(UPDATE_PROVIDER_CONTEXT_SCRIPT_NAME, 'update_context')
    deploy_script(CREATE_INTERNAL_SSL_CERTS_SCRIPT_NAME, 'internal_ssl')


if os.environ.get('set_manager_ip_on_boot').lower() == 'true':
    install_manager_ip_setter()
else:
    ctx.logger.info('Set manager ip on boot is disabled.')

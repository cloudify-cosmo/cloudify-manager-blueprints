#!/usr/bin/env python
#########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.


import os
import json
import random
import string
import base64
import tempfile
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties
SERVICE_NAME = runtime_props['service_name']
ctx_properties = utils.ctx_factory.create(SERVICE_NAME)

CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)
SUDOERS_INCLUDE_DIR = ctx_properties['sudoers_include_dir']


def _random_alphanumeric(result_len=31):
    """
    :return: random string of unique alphanumeric characters
    """
    ascii_alphanumeric = string.ascii_letters + string.digits
    return ''.join(random.sample(ascii_alphanumeric, result_len))


def _deploy_security_configuration():
    ctx.logger.info('Deploying REST Security configuration file...')

    # Generating random hash salt and secret key
    security_configuration = {
        'hash_salt': base64.b64encode(os.urandom(32)),
        'secret_key': base64.b64encode(os.urandom(32)),
        'encoding_alphabet': _random_alphanumeric(),
        'encoding_block_size': 24,
        'encoding_min_length': 5
    }

    os_user = ctx.node.properties['os_user']
    os_group = ctx.node.properties['os_group']

    # Pre-creating paths so permissions fix can work correctly
    # in mgmtworker
    for path in utils.MANAGER_RESOURCES_SNAPSHOT_PATHS:
        utils.mkdir(path)
    utils.chown(
        os_user, os_group,
        utils.MANAGER_RESOURCES_HOME)
    utils.sudo(['ls', '-la', '/opt/manager'])

    current_props = runtime_props['security_configuration']
    current_props.update(security_configuration)
    runtime_props['security_configuration'] = current_props

    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        json.dump(security_configuration, f)
    rest_security_path = join(runtime_props['home_dir'], 'rest-security.conf')
    utils.move(path, rest_security_path)
    utils.chown(os_user, os_group, rest_security_path)


def _create_db_tables_and_add_defaults():
    ctx.logger.info('Creating SQL tables and adding default values...')
    script_name = 'create_tables_and_add_defaults.py'
    source_script_path = join('components/restservice/config', script_name)
    destination_script_path = join(tempfile.gettempdir(), script_name)
    ctx.download_resource(source_script_path, destination_script_path)

    # Directly calling with this python bin, in order to make sure it's run
    # in the correct venv
    python_path = join(runtime_props['home_dir'], 'env', 'bin', 'python')

    args_dict = runtime_props['security_configuration']
    args_dict['postgresql_host'] = runtime_props['postgresql_host']
    args_dict['db_migrate_dir'] = join(
        utils.MANAGER_RESOURCES_HOME,
        'cloudify',
        'migrations'
    )

    # The script won't have access to the ctx, so we dump the relevant args
    # to a JSON file, and pass its path to the script
    args_file_location = join(tempfile.gettempdir(), 'security_config.json')
    with open(args_file_location, 'w') as f:
        json.dump(args_dict, f)

    result = utils.sudo(
        [python_path, destination_script_path, args_file_location]
    )

    _log_results(result)
    utils.remove(args_file_location)
    utils.remove(destination_script_path)


def _log_results(result):
    """Log stdout/stderr output from the script
    """
    if result.aggr_stdout:
        output = result.aggr_stdout.split('\n')
        output = [line.strip() for line in output if line.strip()]
        for line in output[:-1]:
            ctx.logger.debug(line)
        ctx.logger.info(output[-1])
    if result.aggr_stderr:
        output = result.aggr_stderr.split('\n')
        output = [line.strip() for line in output if line.strip()]
        for line in output:
            ctx.logger.error(line)


def _deploy_rest_configuration():
    ctx.logger.info('Deploying REST Service Configuration file...')
    runtime_props['file_server_root'] = utils.MANAGER_RESOURCES_HOME
    utils.deploy_blueprint_resource(
            join(CONFIG_PATH, 'cloudify-rest.conf'),
            join(runtime_props['home_dir'], 'cloudify-rest.conf'),
            SERVICE_NAME)
    utils.chown(ctx.node.properties['os_user'],
                ctx.node.properties['os_group'],
                join(runtime_props['home_dir'], 'cloudify-rest.conf'))


def _allow_creating_cluster():
    env = os.path.join(runtime_props['home_dir'], 'env')
    systemd_run = '/usr/bin/systemd-run'
    journalctl = '/usr/bin/journalctl'
    create_cluster_node = os.path.join(env, 'bin/create_cluster_node')
    cluster_unit_name = 'cloudify-ha-cluster'
    utils.allow_user_to_sudo_command(
        runtime_props,
        ctx.node.properties['os_user'],
        '{0} --unit {1} {2} --config *'
        .format(systemd_run, cluster_unit_name, create_cluster_node),
        description='cluster_start',
        sudoers_include_dir=SUDOERS_INCLUDE_DIR,
    )

    utils.allow_user_to_sudo_command(
        runtime_props,
        ctx.node.properties['os_user'],
        '{0} --unit {1}*'
        .format(journalctl, cluster_unit_name),
        description='cluster_logs',
        sudoers_include_dir=SUDOERS_INCLUDE_DIR
    )


def configure_restservice():
    _deploy_rest_configuration()
    _deploy_security_configuration()
    _allow_creating_cluster()
    utils.systemd.configure(SERVICE_NAME, tmpfiles=True)
    _create_db_tables_and_add_defaults()


configure_restservice()

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
from os.path import join, dirname
import tempfile
import json

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


# TODO: change to /opt/cloudify-rest-service
REST_SERVICE_HOME = '/opt/manager'
REST_SERVICE_NAME = 'restservice'


def _deploy_security_configuration():
    ctx.logger.info('Deploying REST Security configuration file...')
    security_configuration = \
        ctx.instance.runtime_properties['security_configuration']
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        f.write(security_configuration)
    utils.move(path, join(REST_SERVICE_HOME, 'rest-security.conf'))


def _create_db_tables_and_add_users():
    ctx.logger.info('Creating SQL tables and adding admin users...')
    create_script_path = 'components/restservice/config' \
                         '/create_tables_and_add_users.py'
    create_script_destination = join(tempfile.gettempdir(),
                                     'create_tables_and_add_users.py')
    ctx.download_resource(source=create_script_path,
                          destination=create_script_destination)
    # Directly calling with this python bin, in order to make sure it's run
    # in the correct venv
    python_path = '{0}/env/bin/python'.format(REST_SERVICE_HOME)
    runtime_props = ctx.instance.runtime_properties

    # The script won't have access to the ctx, so we dump the relevant args
    # to a JSON file, and pass its path to the script
    args_dict = {
        'security_configuration': runtime_props['security_configuration'],
        'postgresql_db_name': runtime_props['postgresql_db_name'],
        'postgresql_host': runtime_props['postgresql_host']
    }
    args_file_location = join(tempfile.gettempdir(),
                              'security_config.json')
    with open(args_file_location, 'w') as f:
        json.dump(args_dict, f)

    result = utils.sudo(
        [python_path, create_script_destination, args_file_location]
    )

    _log_results(result)
    utils.remove(args_file_location)


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


def configure_restservice():
    _deploy_security_configuration()
    utils.systemd.configure(REST_SERVICE_NAME)
    _create_db_tables_and_add_users()


configure_restservice()

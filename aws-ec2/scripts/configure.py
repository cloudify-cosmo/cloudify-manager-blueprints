########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Built-in Imports
import os
import tempfile

# Third Party Imports
import fabric.api

# Cloudify Imports
from cloudify import ctx
from ec2 import configure
from ec2 import constants


def configure_manager(
        manager_config_path=constants.AWS_DEFAULT_CONFIG_PATH,
        aws_config=None):

    aws_config = aws_config or {}

    _upload_credentials(aws_config, manager_config_path)
    _set_provider_config()


def _upload_credentials(aws_config, manager_config_path):

    if aws_config.get('aws_access_key_id') and \
            aws_config.get('aws_secret_access_key'):
        temp_config = tempfile.mktemp()
        config = configure.BotoConfig()
        credentials = config.create_creds_config(
            aws_config.get('aws_access_key_id'),
            aws_config.get('aws_secret_access_key')
            )
        # This is here because the manager can only use "default".
        # Unless you use a specific region or profile,
        # in which case you need to modify this script.
        config_string = \
            config.create_creds_string(credentials)
        with open(temp_config, 'w') as temp_config_file:
            temp_config_file.write(config_string.getvalue())
    else:
        temp_config = configure.BotoConfig().get_temp_file()

    prepare_dir = \
        'if [ ! -d {0} ]; then mkdir -p {0}; fi'.format(
            os.path.split(manager_config_path)[0])
    make_default_lower = \
        'sed -i "s/\[DEFAULT\]/\[default\]/g" {0}'.format(
            constants.AWS_DEFAULT_CONFIG_PATH)

    fabric.api.run(prepare_dir)
    fabric.api.put(temp_config, manager_config_path)
    fabric.api.run(make_default_lower)


def _set_provider_config():

    resources = dict()
    node_instances = ctx._endpoint.storage.get_node_instances()
    nodes_by_id = \
        {node.id: node for node in ctx._endpoint.storage.get_nodes()}

    node_id_to_provider_context_field = {
        'agents_security_group': 'agents_security_group',
        'agent_keypair': 'agents_keypair'
    }

    for node_instance in node_instances:
        if node_instance.node_id in node_id_to_provider_context_field:
            run_props = node_instance.runtime_properties
            props = nodes_by_id[node_instance.node_id].properties
            provider_context_field = \
                node_id_to_provider_context_field[node_instance.node_id]
            resources[provider_context_field] = {
                'external_resource': props['use_external_resource'],
                'id': run_props[constants.EXTERNAL_RESOURCE_ID],
            }

    provider = {
        'resources': resources
    }

    ctx.instance.runtime_properties['provider_context'] = provider

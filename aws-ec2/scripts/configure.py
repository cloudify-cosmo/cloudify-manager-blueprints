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
import tempfile
from StringIO import StringIO
from ConfigParser import ConfigParser

# Third Party Imports
import fabric.api
from boto.ec2 import get_region

# Cloudify Imports
from cloudify import ctx
from ec2 import constants


def configure_manager(
        manager_config_path=constants.AWS_DEFAULT_CONFIG_PATH,
        aws_config=None):

    aws_config = aws_config or {}

    _upload_credentials(aws_config, manager_config_path)
    _set_provider_config()


def _upload_credentials(aws_config, manager_config_path):

    temp_config = tempfile.mktemp()
    credentials = ConfigParser()

    credentials.add_section('Credentials')
    credentials.set('Credentials', 'aws_access_key_id',
                    aws_config['aws_access_key_id'])
    credentials.set('Credentials', 'aws_secret_access_key',
                    aws_config['aws_secret_access_key'])

    if aws_config.get('ec2_region_name'):
        region = get_region(aws_config['ec2_region_name'])
        credentials.add_section('Boto')
        credentials.set('Boto', 'ec2_region_name',
                        aws_config['ec2_region_name'])
        credentials.set('Boto', 'ec2_region_endpoint',
                        region.endpoint)

    credentials_string = StringIO()
    credentials.write(credentials_string)

    with open(temp_config, 'w') as temp_config_file:
        temp_config_file.write(credentials_string.getvalue())

    make_default_lower = \
        'sed -i "s/\[DEFAULT\]/\[default\]/g" {0}'.format(
            constants.AWS_DEFAULT_CONFIG_PATH)

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

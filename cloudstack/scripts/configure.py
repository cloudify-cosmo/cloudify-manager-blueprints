########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

import tempfile
import json
import logging
from subprocess import call

import fabric
import fabric.api
from fabric.context_managers import settings

from cloudify import ctx
from cloudstack_plugin.cloudstack_common import (
    CLOUDSTACK_ID_PROPERTY,
    CLOUDSTACK_NAME_PROPERTY,
    CLOUDSTACK_TYPE_PROPERTY,
    USE_EXTERNAL_RESOURCE_PROPERTY,
    Config
)
from cloudstack_plugin.floatingip import (
    FLOATINGIP_CLOUDSTACK_TYPE,
    IP_ADDRESS_PROPERTY
)
from cloudify_cli.bootstrap.tasks import (
    PUBLIC_IP_RUNTIME_PROPERTY,
    PROVIDER_RUNTIME_PROPERTY
)


def configure(cloudstack_config):

    manager_public_ip = _configure_public_ip()

    _set_provider_context()

    _copy_cloudstack_configuration_to_manager(manager_public_ip,
                                             cloudstack_config)

def _configure_public_ip():
    floatingip_runtime_props = \
        _get_runtime_props_by_node_name_and_cloudstack_type(
            'manager_server_ip', FLOATINGIP_CLOUDSTACK_TYPE)
    manager_public_ip = floatingip_runtime_props[IP_ADDRESS_PROPERTY]
    ctx.instance.runtime_properties[PUBLIC_IP_RUNTIME_PROPERTY] = \
        manager_public_ip
    return manager_public_ip


def _copy_cloudstack_configuration_to_manager(manager_public_ip,
                                             cloudstack_config):
    tmp = tempfile.mktemp()
    with open(tmp, 'w') as f:
        json.dump(cloudstack_config, f)
    with settings(host_string=manager_public_ip,connection_attempts=5, timeout=5, keepalive=1):
        fabric.api.put(tmp, Config.CLOUDSTACK_CONFIG_PATH_DEFAULT_PATH)


def _get_runtime_props_by_node_name_and_cloudstack_type(
        node_name, node_cloudstack_type):
    node_runtime_props = [v for k, v in ctx.capabilities.get_all().iteritems()
                          if k.startswith(node_name) and
                          v[CLOUDSTACK_TYPE_PROPERTY] == node_cloudstack_type][0]
    return node_runtime_props


def _set_provider_context():
    # Do not use this code section as a reference - it is a workaround for a
    #  deprecated feature and will be removed in the near future

    resources = dict()

    # the reference to storage only works the workflow is executed as a
    # local workflow (i.e. in a local environment context)
    node_instances = ctx._endpoint.storage.get_node_instances()
    nodes_by_id = \
        {node.id: node for node in ctx._endpoint.storage.get_nodes()}

    node_id_to_provider_context_field = {
        'management_subnet': 'subnet',
        'management_network': 'int_network',
        'router': 'router',
        'agents_security_group': 'agents_security_group',
        'management_security_group': 'management_security_group',
        'manager_server_ip': 'floating_ip',
        'external_network': 'ext_network',
        'manager_server': 'management_server',
        'management_keypair': 'management_keypair',
        'agent_keypair': 'agents_keypair'
    }
    for node_instance in node_instances:
        if node_instance.node_id in node_id_to_provider_context_field:
            run_props = node_instance.runtime_properties
            props = nodes_by_id[node_instance.node_id].properties
            provider_context_field = \
                node_id_to_provider_context_field[node_instance.node_id]
            resources[provider_context_field] = {
                'external_resource': props[USE_EXTERNAL_RESOURCE_PROPERTY],
                'type': run_props[CLOUDSTACK_TYPE_PROPERTY],
                'id': run_props[CLOUDSTACK_ID_PROPERTY],
            }
            if node_instance.node_id == 'manager_server_ip':
                resources[provider_context_field]['ip'] = \
                    run_props[IP_ADDRESS_PROPERTY]
            else:
                resources[provider_context_field]['name'] = \
                    run_props[CLOUDSTACK_NAME_PROPERTY]

    provider = {
        'resources': resources
    }

    ctx.instance.runtime_properties[PROVIDER_RUNTIME_PROPERTY] = provider

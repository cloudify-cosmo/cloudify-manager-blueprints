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

import fabric
import fabric.api
from fabric.context_managers import settings

from cloudify import ctx
from openstack_plugin_common import (
    OPENSTACK_NAME_PROPERTY,
    OPENSTACK_TYPE_PROPERTY,
    Config
)
from nova_plugin.server import (
    NETWORKS_PROPERTY,
    SERVER_OPENSTACK_TYPE
)
from neutron_plugin.floatingip import (
    FLOATINGIP_OPENSTACK_TYPE,
    IP_ADDRESS_PROPERTY
)
from neutron_plugin.network import NETWORK_OPENSTACK_TYPE


def configure(openstack_config, agents_private_key_path):

    # configure local
    ctx.runtime_properties['local_agent_key_path'] = agents_private_key_path

    # configure public ip
    floatingip_runtime_props = \
        _get_runtime_props_by_node_name_and_openstack_type(
            'manager_server_ip', FLOATINGIP_OPENSTACK_TYPE)
    manager_public_ip = floatingip_runtime_props[IP_ADDRESS_PROPERTY]
    ctx.runtime_properties['public_ip'] = manager_public_ip

    # configure private ip
    manager_server_networks = \
        _get_runtime_props_by_node_name_and_openstack_type(
            'manager_server', SERVER_OPENSTACK_TYPE)[NETWORKS_PROPERTY]
    management_network = \
        _get_runtime_props_by_node_name_and_openstack_type(
            'management_network',
            NETWORK_OPENSTACK_TYPE)[OPENSTACK_NAME_PROPERTY]
    private_ip = manager_server_networks[management_network][0]
    ctx.runtime_properties['private_ip'] = private_ip

    # place openstack configuration on manager server
    tmp = tempfile.mktemp()

    with open(tmp, 'w') as f:
        json.dump(openstack_config, f)

    with settings(host_string=manager_public_ip):
        fabric.api.put(tmp, Config.OPENSTACK_CONFIG_PATH_DEFAULT_PATH)


def _get_runtime_props_by_node_name_and_openstack_type(
        node_name, node_openstack_type):
    node_runtime_props = [v for k, v in ctx.capabilities.get_all().iteritems()
                          if k.startswith(node_name) and
                          v[OPENSTACK_TYPE_PROPERTY] == node_openstack_type][0]
    return node_runtime_props

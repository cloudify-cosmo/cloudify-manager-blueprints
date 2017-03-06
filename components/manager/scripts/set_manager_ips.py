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


from cloudify import ctx
from cloudify.state import ctx_parameters as inputs
from cloudify.exceptions import NonRecoverableError


source_runtime_props = ctx.source.instance.runtime_properties

# set private ip according to the host ip (backward compatible)
private_ip = ctx.target.instance.host_ip
ctx.logger.debug('Setting manager_configuration private ip to: {0}'.format(
    private_ip))
source_runtime_props['private_ip'] = private_ip

# set public ip from input to this script
public_ip = inputs['public_ip']
ctx.logger.debug('Setting manager_configuration public ip to: {0}'.format(
    public_ip))
source_runtime_props['public_ip'] = public_ip


# If the agent's broker ip is empty, set it to the private ip
# (backward compatible)
agent_configuration = ctx.source.node.properties['cloudify']['cloudify_agent']
broker_ip = agent_configuration.get('broker_ip', '').strip()
if broker_ip:
    source_runtime_props['broker_ip'] = broker_ip
    ctx.logger.debug('broker_ip set to: {0}'.format(
        source_runtime_props['broker_ip']))
else:
    broker_ip = private_ip
    source_runtime_props['broker_ip'] = broker_ip
    ctx.logger.debug(
        'broker_ip is empty, setting to private ip: '
        '{0}'.format(private_ip))


# set the internal REST host according to the REST internal endpoint type
# (public ip / private ip)
rest_host_internal_endpoint_type = inputs['rest_host_internal_endpoint_type']
ctx.logger.debug('rest_host_internal_endpoint_type is: {0}'.format(
    rest_host_internal_endpoint_type))
if rest_host_internal_endpoint_type == 'private_ip':
    source_runtime_props['internal_rest_host'] = private_ip
elif rest_host_internal_endpoint_type == 'public_ip':
    source_runtime_props['internal_rest_host'] = public_ip
else:
    raise NonRecoverableError('invalid rest_host_internal_endpoint_type: "{0}"'
                              ', valid values: "public_ip", "private_ip"'.
                              format(rest_host_internal_endpoint_type))
ctx.logger.debug('internal_rest_host set to: {0}'.format(
    source_runtime_props['internal_rest_host']))

# Set the file server url
file_server_url = 'https://{0}:{1}/resources'.format(
        source_runtime_props['internal_rest_host'],
        source_runtime_props['internal_rest_port']
    )
source_runtime_props['file_server_url'] = file_server_url
ctx.logger.debug('file_server_url set to: {0}'.format(file_server_url))

# set the external REST host according to the REST external endpoint type
# (public ip / private ip)
rest_host_external_endpoint_type = inputs['rest_host_external_endpoint_type']
ctx.logger.debug('rest_host_external_endpoint_type is: {0}'.format(
    rest_host_external_endpoint_type))
if rest_host_external_endpoint_type == 'private_ip':
    source_runtime_props['external_rest_host'] = private_ip
elif rest_host_external_endpoint_type == 'public_ip':
    source_runtime_props['external_rest_host'] = public_ip
else:
    raise NonRecoverableError('invalid rest_host_external_endpoint_type: "{0}"'
                              ', valid values: "public_ip", "private_ip"'.
                              format(rest_host_external_endpoint_type))
ctx.logger.debug('external_rest_host set to: {0}'.format(
    source_runtime_props['external_rest_host']))

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


from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

INTERNAL_REST_CERT_PATH = '/root/cloudify/ssl/internal_rest_host.crt'


target_runtime_props = ctx.target.instance.runtime_properties
source_runtime_props = ctx.source.instance.runtime_properties

rest_host = target_runtime_props['internal_rest_host']
# the file server is accessed through the same address as the rest service
file_server_host = target_runtime_props['internal_rest_host']
rest_protocol = target_runtime_props['rest_protocol']
rest_port = target_runtime_props['rest_port']
security_enabled = target_runtime_props['security_enabled']
ssl_enabled = target_runtime_props['ssl_enabled']
rest_username = target_runtime_props.get('agents_rest_username', '')
rest_password = target_runtime_props.get('agents_rest_password', '')
verify_rest_certificate = \
    target_runtime_props.get('agent_verify_rest_certificate', '')
internal_rest_cert_content = ''
local_rest_cert_file = ''

if verify_rest_certificate.lower() == 'true':
    local_rest_cert_file = INTERNAL_REST_CERT_PATH
    internal_rest_cert_raw = utils.get_file_content(INTERNAL_REST_CERT_PATH)
    internal_rest_cert_content = \
        utils.escape_for_systemd(internal_rest_cert_raw)

source_runtime_props['file_server_host'] = file_server_host
# TODO: find - what is required from the below props?
source_runtime_props['rest_host'] = rest_host
source_runtime_props['rest_protocol'] = rest_protocol
source_runtime_props['rest_port'] = rest_port
source_runtime_props['security_enabled'] = security_enabled
source_runtime_props['rest_username'] = rest_username
source_runtime_props['rest_password'] = rest_password
source_runtime_props['verify_rest_certificate'] = verify_rest_certificate
source_runtime_props['rest_cert_content'] = internal_rest_cert_content
source_runtime_props['local_rest_cert_file'] = local_rest_cert_file

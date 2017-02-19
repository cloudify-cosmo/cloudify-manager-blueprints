#!/usr/bin/env python
# source: mgmtworker -> target: manager_configuration
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


target_runtime_props = ctx.target.instance.runtime_properties
source_runtime_props = ctx.source.instance.runtime_properties

rest_host = target_runtime_props['internal_rest_host']
rest_port = target_runtime_props['internal_rest_port']
broker_ssl_cert_path = target_runtime_props['broker_ssl_cert_path']
local_rest_cert_file = target_runtime_props['internal_cert_path']

# the file server is accessed through the same host and protocol as the rest
# service (externally), but on a different port
file_server_host = target_runtime_props['file_server_host']
file_server_port = target_runtime_props['file_server_port']
file_server_protocol = target_runtime_props['file_server_protocol']


debug_message = 'mgmtworker configuration: \n' \
             'rest_host: {0}\n'\
             'rest_protocol: HTTPS\n' \
             'rest_port: {1}\n' \
             'local_rest_cert_file: {2}\n' \
             'file_server_host: {3}\n' \
             'file_server_port: {4}\n' \
             'file_server_protocol: {5}\n' \
             .format(rest_host, rest_port, local_rest_cert_file,
                     file_server_host, file_server_port, file_server_protocol)
ctx.logger.debug(debug_message)

source_runtime_props['file_server_host'] = file_server_host
source_runtime_props['file_server_port'] = file_server_port
source_runtime_props['file_server_protocol'] = file_server_protocol
source_runtime_props['rest_host'] = rest_host
source_runtime_props['rest_port'] = rest_port
source_runtime_props['local_rest_cert_file'] = local_rest_cert_file
source_runtime_props['broker_ssl_cert_path'] = broker_ssl_cert_path

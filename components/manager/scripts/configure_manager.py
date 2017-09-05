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
    join(dirname(__file__), 'utils.py')
)
import utils  # NOQA

NODE_NAME = 'manager-config'

ctx_properties = ctx.node.properties.get_all()


def configure_security_properties():
    security_config = ctx_properties['security']
    runtime_props = ctx.instance.runtime_properties

    if security_config['ssl']['enabled']:
        # manager SSL settings
        ctx.logger.info('SSL is enabled, setting rest port to 443 and '
                        'rest protocol to https...')
        external_rest_port = 443
        external_rest_protocol = 'https'
    else:
        ctx.logger.info('SSL is disabled, setting rest port '
                        'to 80 and rest protocols to http...')
        external_rest_port = 80
        external_rest_protocol = 'http'

    runtime_props['external_rest_port'] = external_rest_port
    runtime_props['external_rest_protocol'] = external_rest_protocol


def create_certs():
    utils.mkdir(utils.SSL_CERTS_TARGET_DIR)
    utils.generate_ca_cert()
    networks = ctx_properties['cloudify']['cloudify_agent']['networks']
    internal_rest_host = ctx.instance.runtime_properties['internal_rest_host']
    cert_ips = [internal_rest_host] + list(networks.values())
    utils.generate_internal_ssl_cert(ips=cert_ips, name=internal_rest_host)


configure_security_properties()
create_certs()

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

utils.clean_upgrade_resources_if_necessary()
# This MUST be invoked by the first node, before upgrade snapshot is created.
utils.clean_rollback_resources_if_necessary()

ctx_properties = utils.ctx_factory.create(NODE_NAME)


def _disable_requiretty():
    script_dest = '/tmp/disable_requiretty.sh'
    utils.deploy_blueprint_resource('components/manager/scripts'
                                    '/disable_requiretty.sh',
                                    script_dest,
                                    NODE_NAME)

    utils.sudo('chmod +x {0}'.format(script_dest))
    utils.sudo(script_dest)


def _configure_security_properties():

    agent_config = ctx_properties['cloudify']['cloudify_agent']
    security_config = ctx_properties['security']
    security_enabled = security_config['enabled']
    ssl_enabled = security_config['ssl']['enabled']
    ctx.instance.runtime_properties['security_enabled'] = security_enabled
    ctx.instance.runtime_properties['ssl_enabled'] = ssl_enabled
    ctx.instance.runtime_properties['agent_rest_cert_path'] = \
        security_config['agent_rest_cert_path']
    ctx.instance.runtime_properties['broker_ssl_cert_path'] = \
        security_config['broker_ssl_cert_path']

    if security_enabled and ssl_enabled:
        # manager SSL settings
        ctx.logger.info('SSL is enabled, setting rest port to 443 and '
                        'rest protocol to https...')
        ctx.instance.runtime_properties['rest_port'] = 443
        ctx.instance.runtime_properties['rest_protocol'] = 'https'
        # agent SSL settings
        agent_verify_rest_certificate = agent_config['verify_rest_certificate']
        ctx.instance.runtime_properties['agent_verify_rest_certificate'] = \
            agent_verify_rest_certificate
        ctx.logger.debug('agent_verify_rest_certificate: {0}'
                         .format(agent_verify_rest_certificate))
    else:
        ctx.logger.info('Security is off or SSL disabled, setting rest port '
                        'to 80 and rest protocols to http...')
        ctx.instance.runtime_properties['rest_port'] = 80
        ctx.instance.runtime_properties['rest_protocol'] = 'http'

    # set file-server protocol and port
    ctx.instance.runtime_properties['file_server_protocol'] = \
        ctx.instance.runtime_properties['rest_protocol']
    ctx.instance.runtime_properties['file_server_port'] = 53229


def main():
    if utils.is_upgrade:
        utils.create_upgrade_snapshot()
    # TTY has already been disabled. Rollback may not have the script to
    # disable TTY since it has been introduced only on 3.4.1
    if not utils.is_rollback:
        _disable_requiretty()
    _configure_security_properties()


main()

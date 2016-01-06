#!/usr/bin/env python

import subprocess
import os
import importlib

subprocess.check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')

CONFIG_PATH = 'components/nginx/config'

NGINX_SOURCE_URL = ctx.node.properties('nginx_rpm_source_url')
REST_SERVICE_SOURCE_URL = ctx.node.properties('rest_service_module_source_url')

NGINX_LOG_PATH = '/var/log/cloudify/nginx'
MANAGER_RESOURCES_HOME = '/opt/manager/resources'
MANAGER_AGENTS_PATH = '{0}/packages/agents'.format(MANAGER_RESOURCES_HOME)
MANAGER_SCRIPTS_PATH = '{0}/packages/scripts'.format(MANAGER_RESOURCES_HOME)
MANAGER_TEMPLATES_PATH = '{0}/packages/templates'.format(
    MANAGER_RESOURCES_HOME)
NGINX_UNIT_OVERRIDE = '/etc/systemd/system/nginx.service.d'

# this is propagated to the agent retrieval script later on so that it's not
# defined twice.
ctx.instance.runtime_properties(
    'agent_packages_path', value=MANAGER_AGENTS_PATH)

# TODO can we use static (not runtime) attributes for some of these? how to
# set them?
ctx.instance.runtime_properties('default_rest_service_port', value='8100')
ctx.instance.runtime_properties('internal_rest_service_port', value='8101')

ctx.logger.info('Installing Nginx...')
utils.set_selinux_permissive()

utils.copy_notice('nginx')
utils.create_dir(NGINX_LOG_PATH)
utils.create_dir(MANAGER_RESOURCES_HOME)

utils.create_dir(MANAGER_AGENTS_PATH)
utils.create_dir(MANAGER_SCRIPTS_PATH)
utils.create_dir(MANAGER_TEMPLATES_PATH)

utils.create_dir(NGINX_UNIT_OVERRIDE)

utils.yum_install(NGINX_SOURCE_URL)

ctx.logger.info('Creating systemd unit override...')
utils.deploy_blueprint_resource(
    '{0}/restart.conf'.format(CONFIG_PATH),
    '{0}/restart.conf'.format(NGINX_UNIT_OVERRIDE))

utils.deploy_logrotate_config('nginx')
utils.clean_var_log_dir('nginx')

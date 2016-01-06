#!/usr/bin/env python

import subprocess
import os
import importlib

subprocess.check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')


CONFIG_PATH = 'components/logstash/config'
LOGSTASH_UNIT_OVERRIDE = '/etc/systemd/system/logstash.service.d'

LOGSTASH_SOURCE_URL = ctx.node.properties('logstash_rpm_source_url')

RABBITMQ_USERNAME = ctx.node.properties('rabbitmq_username')
RABBITMQ_PASSWORD = ctx.node.properties('rabbitmq_password')

RABBITMQ_ENDPOINT_IP = ctx.node.properties('rabbitmq_endpoint_ip')

LOGSTASH_LOG_PATH = '/var/log/cloudify/logstash'
LOGSTASH_CONF_PATH = '/etc/logstash/conf.d'

# injected as an input to the script
ctx.instance.runtime_properties(
    'es_endpoint_ip', value=os.environ.get('ES_ENDPOINT_IP'))
ctx.instance.runtime_properties(
    'rabbitmq_endpoint_ip', value=utils.get_rabbitmq_endpoint_ip())

# Confirm username and password have been supplied for broker before continuing
# Components other than logstash and riemann have this handled in code already
# Note that these are not directly used in this script, but are used by the
# deployed resources, hence the check here.
if not RABBITMQ_USERNAME or not RABBITMQ_PASSWORD:
    utils.error_exit(
        'Both rabbitmq_username and rabbitmq_password must be supplied and at '
        'least 1 character long in the manager blueprint inputs.')

ctx.logger.info('Installing Logstash...')
utils.set_selinux_permissive()
utils.copy_notice('logstash')

utils.yum_install(LOGSTASH_SOURCE_URL)

utils.create_dir(LOGSTASH_LOG_PATH)
utils.chown('logstash', 'logstash', LOGSTASH_LOG_PATH)


ctx.logger.info('Creating systemd unit override...')
utils.create_dir(LOGSTASH_UNIT_OVERRIDE)
utils.deploy_blueprint_resource(
    '{0}/restart.conf'.format(CONFIG_PATH),
    '{0}/restart.conf'.format(LOGSTASH_UNIT_OVERRIDE))
ctx.logger.info('Deploying Logstash conf...')
utils.deploy_blueprint_resource(
    '{0}/logstash.conf'.format(CONFIG_PATH),
    '{0}/logstash.conf'.format(LOGSTASH_CONF_PATH))

ctx.logger.info('Deploying Logstash sysconfig...')
utils.deploy_blueprint_resource(
    '{0}/logstash'.format(CONFIG_PATH),
    '/etc/sysconfig/logstash')

utils.deploy_logrotate_config('logstash')
# sudo systemctl enable logstash.service
utils.sudo(['/sbin/chkconfig', 'logstash', 'on'])
utils.clean_var_log_dir('logstash')

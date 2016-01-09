#!/usr/bin/env python

import os
from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


CONFIG_PATH = 'components/webui/config'

NODEJS_SOURCE_URL = ctx.node.properties('nodejs_tar_source_url')
WEBUI_SOURCE_URL = ctx.node.properties('webui_tar_source_url')
GRAFANA_SOURCE_URL = ctx.node.properties('grafana_tar_source_url')

# injected as an input to the script
ctx.instance.runtime_properties(
    'influxdb_endpoint_ip', value=os.environ.get('INFLUXDB_ENDPOINT_IP'))

NODEJS_HOME = '/opt/nodejs'
WEBUI_HOME = '/opt/cloudify-ui'
WEBUI_LOG_PATH = '/var/log/cloudify/webui'
GRAFANA_HOME = '{0}/grafana'.format(WEBUI_HOME)

WEBUI_USER = 'webui'
WEBUI_GROUP = 'webui'

ctx.logger.info('Installing Cloudify\'s WebUI...')
utils.set_selinux_permissive()

utils.copy_notice('webui')

utils.create_dir(NODEJS_HOME)
utils.create_dir(WEBUI_HOME)
utils.create_dir('{0}/backend'.format(WEBUI_HOME))
utils.create_dir(WEBUI_LOG_PATH)
utils.create_dir(GRAFANA_HOME)

utils.create_service_user(WEBUI_USER, WEBUI_HOME)

ctx.logger.info('Installing NodeJS...')
nodejs = utils.download_file(NODEJS_SOURCE_URL)
utils.sudo(['tar', '-xzvf', nodejs, '-C', NODEJS_HOME, '--strip=1'])

ctx.logger.info('Installing Cloudify\'s WebUI...')
webui = utils.download_file(WEBUI_SOURCE_URL)
utils.sudo(['tar', '-xzvf', webui, '-C', WEBUI_HOME, '--strip=1'])

ctx.logger.info('Installing Grafana...')
grafana = utils.download_file(GRAFANA_SOURCE_URL)
utils.sudo(['tar', '-xzvf', grafana, '-C', GRAFANA_HOME, '--strip=1'])

ctx.logger.info('Deploying WebUI Configuration...')
utils.deploy_blueprint_resource(
    '{0}/gsPresets.json'.format(CONFIG_PATH),
    '{0}/backend/gsPresets.json'.format(WEBUI_HOME))
ctx.logger.info('Deploying Grafana Configuration...')
utils.deploy_blueprint_resource(
    '{0}/grafana_config.js'.format(CONFIG_PATH),
    '{0}/config.js'.format(GRAFANA_HOME))

ctx.logger.info('Fixing permissions...')
utils.chown(WEBUI_USER, WEBUI_GROUP, WEBUI_HOME)
utils.chown(WEBUI_USER, WEBUI_GROUP, NODEJS_HOME)
utils.chown(WEBUI_USER, WEBUI_GROUP, WEBUI_LOG_PATH)

utils.deploy_logrotate_config('webui')
utils.systemd.configure('webui')

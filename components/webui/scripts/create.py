#!/usr/bin/env python

import os
from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


CONFIG_PATH = 'components/webui/config'


def install_webui():

    nodejs_source_url = ctx.node.properties['nodejs_tar_source_url']
    webui_source_url = ctx.node.properties['webui_tar_source_url']
    grafana_source_url = ctx.node.properties['grafana_tar_source_url']

    # injected as an input to the script
    ctx.instance.runtime_properties['influxdb_endpoint_ip'] = \
        os.environ.get('INFLUXDB_ENDPOINT_IP')

    nodejs_home = '/opt/nodejs'
    webui_home = '/opt/cloudify-ui'
    webui_log_path = '/var/log/cloudify/webui'
    grafana_home = '{0}/grafana'.format(webui_home)

    webui_user = 'webui'
    webui_group = 'webui'

    ctx.logger.info('Installing Cloudify\'s WebUI...')
    utils.set_selinux_permissive()

    utils.copy_notice('webui')

    utils.mkdir(nodejs_home)
    utils.mkdir(webui_home)
    utils.mkdir('{0}/backend'.format(webui_home))
    utils.mkdir(webui_log_path)
    utils.mkdir(grafana_home)

    utils.create_service_user(webui_user, webui_home)

    ctx.logger.info('Installing NodeJS...')
    nodejs = utils.download_file(nodejs_source_url)
    utils.untar(nodejs, nodejs_home)

    ctx.logger.info('Installing Cloudify\'s WebUI...')
    webui = utils.download_file(webui_source_url)
    utils.untar(webui, webui_home)

    ctx.logger.info('Installing Grafana...')
    grafana = utils.download_file(grafana_source_url)
    utils.untar(grafana, grafana_home)

    ctx.logger.info('Deploying WebUI Configuration...')
    utils.deploy_blueprint_resource(
        '{0}/gsPresets.json'.format(CONFIG_PATH),
        '{0}/backend/gsPresets.json'.format(webui_home))
    ctx.logger.info('Deploying Grafana Configuration...')
    utils.deploy_blueprint_resource(
        '{0}/grafana_config.js'.format(CONFIG_PATH),
        '{0}/config.js'.format(grafana_home))

    ctx.logger.info('Fixing permissions...')
    utils.chown(webui_user, webui_group, webui_home)
    utils.chown(webui_user, webui_group, nodejs_home)
    utils.chown(webui_user, webui_group, webui_log_path)

    utils.logrotate('webui')
    utils.systemd.configure('webui')


def main():
    install_webui()


main()

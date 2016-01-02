#!/usr/bin/env python

import importlib
import os
from subprocess import check_output
import time

utils_path = check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
utils = importlib.import_module('utils')


config_path = "components/influxdb/config"

influxdb_source_url = utils.ctx.properties('influxdb_rpm_source_url')
influxdb_endpoint_ip = utils.ctx.properties('influxdb_endpoint_ip')
# currently, cannot be changed due to the webui not allowing to configure it.
influxdb_endpoint_port = '8086'

influxdb_user = 'influxdb'
influxdb_group = 'influxdb'
influxdb_home = '/opt/influxdb'
influxdb_log_path = '/var/log/cloudify/influxdb'


def configure_influxdb(host, port):
    db_user = "root"
    db_pass = "root"
    db_name = "cloudify"

    utils.ctx.logger('Creating InfluxDB Database...')
    utils.run('sudo curl --show-error --silent --retry 5 '
              '"http://{0}:{1}/db?u={2}&p={3}" '
              '-d "{\"name\": \"{4}\"}"'.format(
                  host, port, db_user, db_pass, db_name))


def install_influxdb():
    utils.ctx.logger('Installing InfluxDB...')
    utils.set_selinux_permissive()

    utils.copy_notice('influxdb')
    utils.create_dir(influxdb_home)
    utils.create_dir(influxdb_log_path)

    utils.yum_install(influxdb_source_url)

    utils.ctx.logger('Deploying InfluxDB config.toml...')
    utils.deploy_blueprint_resource(
        '{0}/config.toml'.format(config_path),
        '{0}/shared/config.toml'.format(influxdb_home))

    utils.ctx.logger('Fixing user permissions...')
    utils.chown(influxdb_user, influxdb_group, influxdb_home)
    utils.chown(influxdb_user, influxdb_group, influxdb_log_path)

    utils.configure_systemd_service('influxdb')


if influxdb_endpoint_ip:
    utils.ctx.logger('External InfluxDB Endpoint IP provided: {0}'.format(
        influxdb_endpoint_ip))
    time.sleep(5)
    utils.wait_for_port(influxdb_endpoint_port, influxdb_endpoint_ip)
    configure_influxdb(influxdb_endpoint_ip, influxdb_endpoint_port)
else:
    influxdb_endpoint_ip = utils.ctx.host_ip()
    install_influxdb()

    utils.ctx.logger('Starting InfluxDB Service...')
    utils.start_systemd_service('cloudify-influxdb')

    utils.wait_for_port(influxdb_endpoint_port, influxdb_endpoint_ip)
    configure_influxdb(influxdb_endpoint_ip, influxdb_endpoint_port)

    utils.ctx.logger('Stopping InfluxDB Service...')
    utils.stop_systemd_service('cloudify-influxdb')


utils.ctx.runtime_properties('influxdb_endpoint_ip', influxdb_endpoint_ip)

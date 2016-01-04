#!/usr/bin/env python

import subprocess
import os
import importlib
import time
import json
import sys

subprocess.check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')


CONFIG_PATH = "components/influxdb/config"

INFLUXDB_SOURCE_URL = ctx.node.properties('influxdb_rpm_source_url')
INFLUXDB_ENDPOINT_IP = ctx.node.properties('influxdb_endpoint_ip')
# currently, cannot be changed due to the webui not allowing to configure it.
INFLUXDB_ENDPOINT_PORT = 8086

INFLUXDB_USER = 'influxdb'
INFLUXDB_GROUP = 'influxdb'
INFLUXDB_HOME = '/opt/influxdb'
INFLUXDB_LOG_PATH = '/var/log/cloudify/influxdb'


def configure_influxdb(host, port):
    db_user = "root"
    db_pass = "root"
    db_name = "cloudify"

    ctx.logger.info('Creating InfluxDB Database...')

    # the below request is equivalent to running:
    # curl -S -s --retry 5 "http://localhost:8086/db?u=root&p=root" '-d "{\"name\": \"cloudify\"}"  # NOQA
    import urllib
    import urllib2

    endpoint = 'http://{0}:{1}/db'.format(host, port)
    params = urllib.urlencode(dict(u=db_user, p=db_pass))
    data = {'name': db_name}
    url = endpoint + '?' + params

    # check if db already exists
    db_list = eval(urllib2.urlopen(urllib2.Request(url)).read())
    try:
        assert not any(d.get('name') == db_name for d in db_list)
    except AssertionError:
        ctx.logger.info('Database {0} already exists!'.format(db_name))
        return

    ctx.logger.info('Request is: {0} \'{1}\''.format(url, data))

    try:
        urllib2.urlopen(urllib2.Request(url, json.dumps(data)))
    except Exception as ex:
        ctx.logger.info('Failed to create: {0} ({1}).'.format(db_name, ex))
        sys.exit(1)

    # verify db created
    ctx.logger.info('Verifying database create successfully...')
    db_list = eval(urllib2.urlopen(urllib2.Request(url)).read())
    try:
        assert any(d.get('name') == db_name for d in db_list)
    except AssertionError:
        ctx.logger.info('Verification failed!')
        sys.exit(1)


def install_influxdb():
    ctx.logger.info('Installing InfluxDB...')
    utils.set_selinux_permissive()

    utils.copy_notice('influxdb')
    utils.create_dir(INFLUXDB_HOME)
    utils.create_dir(INFLUXDB_LOG_PATH)

    utils.yum_install(INFLUXDB_SOURCE_URL)

    ctx.logger.info('Deploying InfluxDB config.toml...')
    utils.deploy_blueprint_resource(
        '{0}/config.toml'.format(CONFIG_PATH),
        '{0}/shared/config.toml'.format(INFLUXDB_HOME))

    ctx.logger.info('Fixing user permissions...')
    utils.chown(INFLUXDB_USER, INFLUXDB_GROUP, INFLUXDB_HOME)
    utils.chown(INFLUXDB_USER, INFLUXDB_GROUP, INFLUXDB_LOG_PATH)

    utils.systemd.configure('influxdb')


if INFLUXDB_ENDPOINT_IP:
    influxdb_endpoint_ip = INFLUXDB_ENDPOINT_IP
    ctx.logger.info('External InfluxDB Endpoint IP provided: {0}'.format(
        INFLUXDB_ENDPOINT_IP))
    time.sleep(5)
    utils.wait_for_port(INFLUXDB_ENDPOINT_PORT, INFLUXDB_ENDPOINT_IP)
    configure_influxdb(INFLUXDB_ENDPOINT_IP, INFLUXDB_ENDPOINT_PORT)
else:

    influxdb_endpoint_ip = ctx.instance.host_ip()
    install_influxdb()

    ctx.logger.info('Starting InfluxDB Service...')
    utils.systemd.start('cloudify-influxdb')

    utils.wait_for_port(INFLUXDB_ENDPOINT_PORT, influxdb_endpoint_ip)
    configure_influxdb(influxdb_endpoint_ip, INFLUXDB_ENDPOINT_PORT)

    ctx.logger.info('Stopping InfluxDB Service...')
    utils.systemd.stop('cloudify-influxdb')


ctx.instance.runtime_properties('influxdb_endpoint_ip', influxdb_endpoint_ip)

#!/usr/bin/env python

import time
import json
import sys
from os.path import (join as jn, dirname as dn)

from cloudify import ctx
# if we use download_resource_and_render here instead we might be able
# to automatically provide some service specific context instead of passing it
# to a specific invocation of a util
ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


CONFIG_PATH = "components/influxdb/config"


def configure_influxdb(host, port):
    db_user = "root"
    db_pass = "root"
    db_name = "cloudify"

    ctx.logger.info('Creating InfluxDB Database...')

    # the below request is equivalent to running:
    # curl -S -s "http://localhost:8086/db?u=root&p=root" '-d "{\"name\": \"cloudify\"}"  # NOQA
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
    ctx.logger.info('Databased {0} created successfully.'.format(db_name))


def install_influxdb():

    influxdb_source_url = ctx.node.properties['influxdb_rpm_source_url']

    influxdb_user = 'influxdb'
    influxdb_group = 'influxdb'
    influxdb_home = '/opt/influxdb'
    influxdb_log_path = '/var/log/cloudify/influxdb'

    ctx.logger.info('Installing InfluxDB...')
    utils.set_selinux_permissive()

    utils.copy_notice('influxdb')
    utils.mkdir(influxdb_home)
    utils.mkdir(influxdb_log_path)

    utils.yum_install(influxdb_source_url)
    utils.sudo(['rm', '-rf', '/etc/init.d/influxdb'])

    ctx.logger.info('Deploying InfluxDB config.toml...')
    utils.deploy_blueprint_resource(
        '{0}/config.toml'.format(CONFIG_PATH),
        '{0}/shared/config.toml'.format(influxdb_home))

    ctx.logger.info('Fixing user permissions...')
    utils.chown(influxdb_user, influxdb_group, influxdb_home)
    utils.chown(influxdb_user, influxdb_group, influxdb_log_path)

    utils.systemd.configure('influxdb')


def main():

    influxdb_endpoint_ip = ctx.node.properties['influxdb_endpoint_ip']
    # currently, cannot be changed due to webui not allowing to configure it.
    influxdb_endpoint_port = 8086

    if influxdb_endpoint_ip:
        ctx.logger.info('External InfluxDB Endpoint IP provided: {0}'.format(
            influxdb_endpoint_ip))
        time.sleep(5)
        utils.wait_for_port(influxdb_endpoint_port, influxdb_endpoint_ip)
        configure_influxdb(influxdb_endpoint_ip, influxdb_endpoint_port)
    else:
        influxdb_endpoint_ip = ctx.instance.host_ip
        install_influxdb()

        ctx.logger.info('Starting InfluxDB Service...')
        utils.systemd.start('cloudify-influxdb')

        utils.wait_for_port(influxdb_endpoint_port, influxdb_endpoint_ip)
        configure_influxdb(influxdb_endpoint_ip, influxdb_endpoint_port)

        ctx.logger.info('Stopping InfluxDB Service...')
        utils.systemd.stop('cloudify-influxdb')

    ctx.instance.runtime_properties['influxdb_endpoint_ip'] = \
        influxdb_endpoint_ip


main()

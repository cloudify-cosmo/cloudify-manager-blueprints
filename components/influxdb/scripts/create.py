#!/usr/bin/env python

import time
import json
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'influxdb'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME
runtime_props['service_user'] = SERVICE_NAME
runtime_props['service_group'] = SERVICE_NAME

HOME_DIR = join('/opt', SERVICE_NAME)
LOG_DIR = join(utils.BASE_LOG_DIR, SERVICE_NAME)
INIT_D_PATH = join('/etc', 'init.d', SERVICE_NAME)
runtime_props['files_to_remove'] = [HOME_DIR, LOG_DIR, INIT_D_PATH]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)
CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)


def _configure_influxdb(host, port):
    db_user = "root"
    db_pass = "root"
    db_name = "cloudify"

    ctx.logger.info('Creating InfluxDB Database...')

    # the below request is equivalent to running:
    # curl -S -s "http://localhost:8086/db?u=root&p=root" '-d "{\"name\": \"cloudify\"}"  # NOQA
    import urllib
    import urllib2
    import ast

    endpoint_for_list = 'http://{0}:{1}/db'.format(host, port)
    endpoint_for_creation = ('http://{0}:{1}/cluster/database_configs/'
                             '{2}'.format(host, port, db_name))
    params = urllib.urlencode(dict(u=db_user, p=db_pass))
    url_for_list = endpoint_for_list + '?' + params
    url_for_creation = endpoint_for_creation + '?' + params

    # check if db already exists
    db_list = eval(urllib2.urlopen(urllib2.Request(url_for_list)).read())
    try:
        assert not any(d.get('name') == db_name for d in db_list)
    except AssertionError:
        ctx.logger.info('Database {0} already exists!'.format(db_name))
        return

    try:
        utils.deploy_blueprint_resource(
            '{0}/retention.json'.format(CONFIG_PATH),
            '/tmp/retention.json', SERVICE_NAME)
        with open('/tmp/retention.json') as policy_file:
            retention_policy = policy_file.read()
        ctx.logger.debug(
            'Using retention policy: \n{0}'.format(retention_policy))
        data = json.dumps(ast.literal_eval(retention_policy))
        ctx.logger.debug('Using retention policy: \n{0}'.format(data))
        content_length = len(data)
        request = urllib2.Request(url_for_creation, data, {
            'Content-Type': 'application/json',
            'Content-Length': content_length})
        ctx.logger.debug('Request is: {0}'.format(request))
        request_reader = urllib2.urlopen(request)
        response = request_reader.read()
        ctx.logger.debug('Response: {0}'.format(response))
        request_reader.close()
        utils.remove('/tmp/retention.json')

    except Exception as ex:
        ctx.abort_operation('Failed to create: {0} ({1}).'.format(db_name, ex))

    # verify db created
    ctx.logger.info('Verifying database create successfully...')
    db_list = eval(urllib2.urlopen(urllib2.Request(url_for_list)).read())
    try:
        assert any(d.get('name') == db_name for d in db_list)
    except AssertionError:
        ctx.abort_operation('Verification failed!')
    ctx.logger.info('Databased {0} created successfully.'.format(db_name))


def _install_influxdb():

    influxdb_source_url = ctx_properties['influxdb_rpm_source_url']

    influxdb_user = 'influxdb'
    influxdb_group = 'influxdb'

    ctx.logger.info('Installing InfluxDB...')
    utils.set_selinux_permissive()

    utils.copy_notice(SERVICE_NAME)
    utils.mkdir(HOME_DIR)
    utils.mkdir(LOG_DIR)

    utils.yum_install(influxdb_source_url, service_name=SERVICE_NAME)

    ctx.logger.info('Deploying InfluxDB configuration...')
    utils.deploy_blueprint_resource(
        '{0}/config.toml'.format(CONFIG_PATH),
        '{0}/shared/config.toml'.format(HOME_DIR),
        SERVICE_NAME)

    utils.chown(influxdb_user, influxdb_group, HOME_DIR)
    utils.chown(influxdb_user, influxdb_group, LOG_DIR)

    utils.systemd.configure(SERVICE_NAME)
    # Provided with InfluxDB's package. Will be removed if it exists.
    utils.remove(INIT_D_PATH)
    utils.logrotate(SERVICE_NAME)


def main():

    influxdb_endpoint_ip = ctx_properties['influxdb_endpoint_ip']
    # currently, cannot be changed due to webui not allowing to configure it.
    influxdb_endpoint_port = 8086

    if influxdb_endpoint_ip:
        ctx.logger.info('External InfluxDB Endpoint IP provided: {0}'.format(
            influxdb_endpoint_ip))
        time.sleep(5)
        utils.wait_for_port(influxdb_endpoint_port, influxdb_endpoint_ip)
        _configure_influxdb(influxdb_endpoint_ip, influxdb_endpoint_port)
    else:
        influxdb_endpoint_ip = ctx.instance.host_ip
        _install_influxdb()

        utils.systemd.restart(SERVICE_NAME)

        utils.wait_for_port(influxdb_endpoint_port, influxdb_endpoint_ip)
        _configure_influxdb(influxdb_endpoint_ip, influxdb_endpoint_port)

        utils.systemd.stop(SERVICE_NAME)

    ctx.instance.runtime_properties['influxdb_endpoint_ip'] = \
        influxdb_endpoint_ip


main()

#!/usr/bin/env python

from os.path import (
    basename,
    dirname,
    join,
)

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'logstash'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME

HOME_DIR = join('/opt', SERVICE_NAME)
LOG_DIR = join(utils.BASE_LOG_DIR, SERVICE_NAME)
UNIT_OVERRIDE_PATH = '/etc/systemd/system/logstash.service.d'
runtime_props['files_to_remove'] = [HOME_DIR, LOG_DIR, UNIT_OVERRIDE_PATH]

# Used in the service template
runtime_props['log_dir'] = LOG_DIR

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)
CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)


def install_plugin(name, plugin_url):
    """Install plugin.

    :param name: Plugin name
    :type name: str
    :param plugin_url: Plugin file location
    :type plugin_path: str

    """
    ctx.logger.info('Installing {} plugin...'.format(name))
    plugin_path = utils.download_cloudify_resource(
        plugin_url, service_name=SERVICE_NAME)

    # Use /dev/urandom to get entropy faster while installing plugins
    utils.run([
        'sudo', '-u', 'logstash',
        'sh', '-c',
        (
            'export JRUBY_OPTS=-J-Djava.security.egd=file:/dev/urandom; '
            '/opt/logstash/bin/plugin install {0}'.format(plugin_path)
        )
    ])


def install_logstash_filter_json_encode_plugin():
    """"Install filter plugin needed to encode json data."""
    name = 'logstash-filter-json_encode'
    plugin_url = ctx_properties['logstash_filter_json_encode_plugin_url']
    install_plugin(name, plugin_url)


def install_logstash_output_jdbc_plugin():
    """"Install output plugin needed to write to SQL databases."""
    name = 'logstash-output-jdbc'
    plugin_url = ctx_properties['logstash_output_jdbc_plugin_url']
    install_plugin(name, plugin_url)


def install_postgresql_jdbc_driver():
    """Install driver used by the jdbc plugin to write data to postgresql."""
    jdbc_driver_url = ctx_properties['postgresql_jdbc_driver_url']

    ctx.logger.info('Installing PostgreSQL JDBC driver...')
    jar_path = join(HOME_DIR, 'vendor', 'jar')
    jdbc_path = join(jar_path, 'jdbc')
    utils.mkdir(jdbc_path)
    utils.chown('logstash', 'logstash', jar_path)
    driver_path = utils.download_cloudify_resource(
        jdbc_driver_url, service_name=SERVICE_NAME)
    utils.run([
        'sudo', '-u', 'logstash',
        'cp',
        driver_path,
        join(jdbc_path, basename(jdbc_driver_url)),
    ])


def install_logstash():
    """Install logstash as a systemd service."""
    logstash_source_url = ctx_properties['logstash_rpm_source_url']

    ctx.logger.info('Installing Logstash...')
    utils.set_selinux_permissive()
    utils.copy_notice(SERVICE_NAME)

    utils.yum_install(logstash_source_url, SERVICE_NAME)

    install_logstash_filter_json_encode_plugin()
    install_logstash_output_jdbc_plugin()
    install_postgresql_jdbc_driver()

    utils.mkdir(LOG_DIR)
    utils.chown('logstash', 'logstash', LOG_DIR)

    ctx.logger.debug('Creating systemd unit override...')
    utils.mkdir(UNIT_OVERRIDE_PATH)
    utils.deploy_blueprint_resource(
        '{0}/restart.conf'.format(CONFIG_PATH),
        '{0}/restart.conf'.format(UNIT_OVERRIDE_PATH),
        SERVICE_NAME)


if __name__ == '__main__':
    install_logstash()

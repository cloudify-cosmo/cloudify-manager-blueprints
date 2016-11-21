#!/usr/bin/env python

import tempfile

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


CONFIG_PATH = 'components/logstash/config'
LOGSTASH_SERVICE_NAME = 'logstash'

ctx_properties = utils.ctx_factory.create(LOGSTASH_SERVICE_NAME)


def install_logstash_output_jdbc_plugin():
    """"Install output plugin needed to write to SQL databases."""
    plugin_url = ctx_properties['logstash_output_jdbc_plugin_url']
    plugin_url = (
        'https://rubygems.org/downloads/logstash-output-jdbc-0.2.10.gem'
    )

    ctx.logger.info('Installing logstash-output-jdbc plugin...')
    plugin_path = join(tempfile.gettempdir(), basename(plugin_url))
    utils.download_file(plugin_url, plugin_path)
    utils.run([
        'sudo', '-u', 'logstash',
        '/opt/logstash/bin/plugin', 'install', plugin_path,
    ])


def install_postgresql_jdbc_driver():
    """Install driver used by the jdbc plugin to write data to postgresql."""
    driver_url = ctx_properties['postgresql_jdbc_driver_url']

    ctx.logger.info('Installing PostgreSQL JDBC driver...')
    jar_path = '/opt/logstash/vendor/jar'
    jdbc_path = join(jar_path, 'jdbc')
    utils.mkdir(jdbc_path)
    utils.chown('logstash', 'logstash', jar_path)
    driver_path = utils.download_file(driver_url)
    utils.run([
        'sudo', '-u', 'logstash',
        'cp',
        driver_path,
        join(jdbc_path, basename(driver_url)),
    ])


def create_postgresql_tables():
    """Create database tables to store log/event information."""
    ctx.logger.info('Creating PostgreSQL tables...')

    utils.run([
        'sudo', '-u', 'postgres',
        'psql', 'cloudify_db', '-c',
        (
            'CREATE TABLE {0} ('
            'timestamp TIMESTAMP,'
            'context JSONB,'
            'logger TEXT,'
            'level TEXT,'
            'message JSONB,'
            'message_code TEXT'
            ');'
            'ALTER TABLE {0} OWNER TO cloudify;'
            .format('logs')
        )
    ])

    utils.run([
        'sudo', '-u', 'postgres',
        'psql', 'cloudify_db', '-c',
        (
            'CREATE TABLE {0} ('
            'timestamp TIMESTAMP,'
            'context JSONB,'
            'event_type TEXT,'
            'message JSONB,'
            'message_code TEXT'
            ');'
            'ALTER TABLE {0} OWNER TO cloudify;'
            .format('events')
        )
    ])


def install_logstash():
    """Install logstash as a systemd service."""
    logstash_unit_override = '/etc/systemd/system/logstash.service.d'

    logstash_source_url = ctx_properties['logstash_rpm_source_url']
    logstash_log_path = '/var/log/cloudify/logstash'

    ctx.logger.info('Installing Logstash...')
    utils.set_selinux_permissive()
    utils.copy_notice(LOGSTASH_SERVICE_NAME)

    utils.yum_install(logstash_source_url, service_name=LOGSTASH_SERVICE_NAME)

    install_logstash_output_jdbc_plugin()
    install_postgresql_jdbc_driver()
    create_postgresql_tables()

    utils.mkdir(logstash_log_path)
    utils.chown('logstash', 'logstash', logstash_log_path)

    ctx.logger.debug('Creating systemd unit override...')
    utils.mkdir(logstash_unit_override)
    utils.deploy_blueprint_resource(
        '{0}/restart.conf'.format(CONFIG_PATH),
        '{0}/restart.conf'.format(logstash_unit_override),
        LOGSTASH_SERVICE_NAME)


if __name__ == '__main__':
    install_logstash()

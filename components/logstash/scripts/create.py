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


CONFIG_PATH = 'components/logstash/config'
LOGSTASH_SERVICE_NAME = 'logstash'

ctx_properties = utils.ctx_factory.create(LOGSTASH_SERVICE_NAME)


def install_logstash():

    logstash_unit_override = '/etc/systemd/system/logstash.service.d'

    logstash_source_url = ctx_properties['logstash_rpm_source_url']
    postgresql_jdbc_driver_url = (
        'https://jdbc.postgresql.org/download/postgresql-9.4.1212.jar'
    )

    logstash_log_path = '/var/log/cloudify/logstash'

    ctx.logger.info('Installing Logstash...')
    utils.set_selinux_permissive()
    utils.copy_notice(LOGSTASH_SERVICE_NAME)

    utils.yum_install(logstash_source_url, service_name=LOGSTASH_SERVICE_NAME)

    ctx.logger.info('Installing logstash-output-jdbc plugin...')
    utils.run([
        'sudo', '-u', 'logstash',
        '/opt/logstash/bin/plugin', 'install', 'logstash-output-jdbc',
    ])

    ctx.logger.info('Installing PostgreSQL JDBC driver...')
    jar_path = '/opt/logstash/vendor/jar'
    jdbc_path = join(jar_path, 'jdbc')
    utils.mkdir(jdbc_path)
    utils.chown('logstash', 'logstash', jar_path)
    utils.download_file(
        postgresql_jdbc_driver_url,
        join(jdbc_path, basename(postgresql_jdbc_driver_url)),
    )

    ctx.logger.info('Creating PostgreSQL tables...')
    for table_name in ['logs', 'events']:
        utils.run([
            'sudo', '-u', 'postgres',
            'psql', 'cloudify_db', '-c',
            (
                'CREATE TABLE {0} (timestamp TIMESTAMP, message TEXT);'
                'ALTER TABLE {0} OWNER TO cloudify;'
                .format(table_name)
            )
        ])

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

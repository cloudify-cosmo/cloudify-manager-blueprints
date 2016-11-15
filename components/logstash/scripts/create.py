#!/usr/bin/env python

import os
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

    rabbitmq_username = ctx_properties['rabbitmq_username']
    rabbitmq_password = ctx_properties['rabbitmq_password']

    logstash_log_path = '/var/log/cloudify/logstash'

    # injected as an input to the script
    ctx.instance.runtime_properties['es_endpoint_ip'] = \
        os.environ['ES_ENDPOINT_IP']
    elasticsearch_props = utils.ctx_factory.get('elasticsearch')
    ctx.instance.runtime_properties['es_endpoint_port'] = \
        elasticsearch_props['es_endpoint_port']

    rabbit_props = utils.ctx_factory.get('rabbitmq')
    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = \
        utils.get_rabbitmq_endpoint_ip(
            rabbit_props.get('rabbitmq_endpoint_ip'))
    ctx.instance.runtime_properties['rabbitmq_username'] = \
        rabbit_props['rabbitmq_username']
    ctx.instance.runtime_properties['rabbitmq_password'] = \
        rabbit_props['rabbitmq_password']

    # Confirm username and password have been supplied for broker before
    # continuing.
    # Components other than logstash and riemann have this handled in code.
    # Note that these are not directly used in this script, but are used by the
    # deployed resources, hence the check here.
    if not rabbitmq_username or not rabbitmq_password:
        ctx.abort_operation(
            'Both rabbitmq_username and rabbitmq_password must be supplied '
            'and at least 1 character long in the manager blueprint inputs.')

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
    utils.download_file(
        postgresql_jdbc_driver_url,
        join(
            '/opt/logstash/vendor/jar/jdbc',
            basename(postgresql_jdbc_driver_url),
        ),
    )
    utils.chown('logstash', 'logstash', '/opt/logstash/vendor/jar')

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

#!/usr/bin/env python

import os
import time
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'rabbitmq'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME

HOME_DIR = join('/etc', SERVICE_NAME)
LOG_DIR = join(utils.BASE_LOG_DIR, SERVICE_NAME)
FD_LIMIT_PATH = '/etc/security/limits.d/rabbitmq.conf'
runtime_props['files_to_remove'] = [HOME_DIR, LOG_DIR, FD_LIMIT_PATH]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)
CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)


def check_if_user_exists(username):
    if username in utils.sudo(
            ['rabbitmqctl', 'list_users'], retries=5).aggr_stdout:
        return True
    return False


def _clear_guest_permissions_if_guest_exists():
    if check_if_user_exists('guest'):
        ctx.logger.info('Disabling RabbitMQ guest user...')
        utils.sudo(['rabbitmqctl', 'clear_permissions', 'guest'], retries=5)
        utils.sudo(['rabbitmqctl', 'delete_user', 'guest'], retries=5)


def _create_user_and_set_permissions(rabbitmq_username,
                                     rabbitmq_password):
    if not check_if_user_exists(rabbitmq_username):
        ctx.logger.info('Creating new user and setting permissions...'.format(
            rabbitmq_username, rabbitmq_password))
        utils.sudo(['rabbitmqctl', 'add_user',
                    rabbitmq_username, rabbitmq_password])
        utils.sudo(['rabbitmqctl', 'set_permissions',
                    rabbitmq_username, '.*', '.*', '.*'], retries=5)
        utils.sudo(['rabbitmqctl', 'set_user_tags', rabbitmq_username,
                    'administrator'])


def _install_rabbitmq():
    erlang_rpm_source_url = ctx_properties['erlang_rpm_source_url']
    rabbitmq_rpm_source_url = ctx_properties['rabbitmq_rpm_source_url']
    # TODO: maybe we don't need this env var
    os.putenv('RABBITMQ_FD_LIMIT', str(ctx_properties['rabbitmq_fd_limit']))
    rabbitmq_username = ctx_properties['rabbitmq_username']
    rabbitmq_password = ctx_properties['rabbitmq_password']

    ctx.logger.info('Installing RabbitMQ...')
    utils.set_selinux_permissive()

    utils.copy_notice(SERVICE_NAME)
    utils.mkdir(LOG_DIR)

    utils.yum_install(erlang_rpm_source_url, service_name=SERVICE_NAME)
    utils.yum_install(rabbitmq_rpm_source_url, service_name=SERVICE_NAME)

    utils.logrotate(SERVICE_NAME)

    utils.systemd.configure(SERVICE_NAME)

    ctx.logger.info('Configuring File Descriptors Limit...')
    utils.deploy_blueprint_resource(
        '{0}/rabbitmq_ulimit.conf'.format(CONFIG_PATH),
        FD_LIMIT_PATH,
        SERVICE_NAME)

    utils.deploy_blueprint_resource(
        '{0}/rabbitmq-definitions.json'.format(CONFIG_PATH),
        join(HOME_DIR, 'definitions.json'),
        SERVICE_NAME)

    # This stops rabbit from failing if the host name changes, e.g. when
    # a manager is deployed from an image but given a new hostname.
    # This is likely to cause problems with clustering of rabbitmq if this is
    # done at any point, so at that point a change to the file and cleaning of
    # mnesia would likely be necessary.
    utils.deploy_blueprint_resource(
        '{0}/rabbitmq-env.conf'.format(CONFIG_PATH),
        '/etc/rabbitmq/rabbitmq-env.conf',
        SERVICE_NAME)
    # Delete old mnesia node
    utils.sudo(['rm', '-rf', '/var/lib/rabbitmq/mnesia'])

    utils.systemd.systemctl('daemon-reload')

    utils.chown('rabbitmq', 'rabbitmq', LOG_DIR)

    # rabbitmq restart exits with 143 status code that is valid in this case.
    utils.systemd.restart(SERVICE_NAME, ignore_failure=True)

    time.sleep(10)
    utils.wait_for_port(5672)

    ctx.logger.info('Enabling RabbitMQ Plugins...')
    # Occasional timing issues with rabbitmq starting have resulted in
    # failures when first trying to enable plugins
    utils.sudo(['rabbitmq-plugins', 'enable', 'rabbitmq_management'],
               retries=5)
    utils.sudo(['rabbitmq-plugins', 'enable', 'rabbitmq_tracing'], retries=5)

    _clear_guest_permissions_if_guest_exists()
    _create_user_and_set_permissions(rabbitmq_username, rabbitmq_password)

    utils.deploy_blueprint_resource(
        '{0}/rabbitmq.config'.format(CONFIG_PATH),
        join(HOME_DIR, 'rabbitmq.config'),
        SERVICE_NAME, user_resource=True)

    utils.systemd.stop(SERVICE_NAME, retries=5)


def main():
    broker_ip = ctx.instance.host_ip
    _install_rabbitmq()
    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = broker_ip


main()

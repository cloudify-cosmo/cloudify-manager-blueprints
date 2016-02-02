#!/usr/bin/env python

from os.path import (join as jn, dirname as dn)
import sys
import os
from time import sleep

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils

CONFIG_PATH = 'components/rabbitmq/config'


def check_if_user_exists(username):
    if username in utils.sudo(
            ['rabbitmqctl', 'list_users'], retries=5).aggr_stdout:
        return True
    return False


def clear_guest_permissions_if_guest_exists():
    if check_if_user_exists('guest'):
        ctx.logger.info('Disabling RabbitMQ guest user')
        utils.sudo(['rabbitmqctl', 'clear_permissions', 'guest'], retries=5)
        utils.sudo(['rabbitmqctl', 'delete_user', 'guest'], retries=5)


def create_rabbit_mq_user_and_set_permissions(rabbitmq_username,
                                              rabbitmq_password):
    if not check_if_user_exists(rabbitmq_username):
        ctx.logger.info('Creating new RabbitMQ user and setting permissions')
        utils.sudo(['rabbitmqctl', 'add_user',
                    rabbitmq_username, rabbitmq_password])
        utils.sudo(['rabbitmqctl', 'set_permissions',
                    rabbitmq_username, '.*', '.*', '.*'], retries=5)


def set_rabbit_mq_security(rabbitmq_ssl_enabled,
                           rabbitmq_cert_private,
                           rabbitmq_cert_public):
    # Deploy certificates if both have been provided.
    # Complain loudly if one has been provided and the other hasn't.
    if rabbitmq_ssl_enabled:
        if rabbitmq_cert_private and rabbitmq_cert_public:
            utils.deploy_ssl_certificate(
                    'private', '/etc/rabbitmq/rabbit-priv.pem',
                    'rabbitmq', rabbitmq_cert_private)
            utils.deploy_ssl_certificate(
                    'public', '/etc/rabbitmq/rabbit-pub.pem',
                    'rabbitmq', rabbitmq_cert_public)
            # Configure for SSL
            utils.deploy_blueprint_resource(
                    '{0}/rabbitmq.config-ssl'.format(CONFIG_PATH),
                    '/etc/rabbitmq/rabbitmq.config')
        else:
            ctx.logger.error('When providing a certificate for rabbitmq, '
                             'both public and private certificates must be '
                             'supplied.')
            sys.exit(1)
    else:
        utils.deploy_blueprint_resource(
                '{0}/rabbitmq.config-nossl'.format(CONFIG_PATH),
                '/etc/rabbitmq/rabbitmq.config')
        if rabbitmq_cert_private or rabbitmq_cert_public:
            ctx.logger.warn('Broker SSL cert supplied but SSL not enabled '
                            '(broker_ssl_enabled is False).')

#TODO: remove all putenv
def install_rabbitmq():
    erlang_rpm_source_url = ctx.node.properties['erlang_rpm_source_url']
    rabbitmq_rpm_source_url = ctx.node.properties['rabbitmq_rpm_source_url']
    # TODO: maybe we don't need this env var
    os.putenv('RABBITMQ_FD_LIMIT',
              str(ctx.node.properties['rabbitmq_fd_limit']))
    rabbitmq_log_path = '/var/log/cloudify/rabbitmq'
    rabbitmq_username = ctx.node.properties['rabbitmq_username']
    rabbitmq_password = ctx.node.properties['rabbitmq_password']
    rabbitmq_cert_public = ctx.node.properties['rabbitmq_cert_public']
    rabbitmq_ssl_enabled = ctx.node.properties['rabbitmq_ssl_enabled']
    rabbitmq_cert_private = ctx.node.properties['rabbitmq_cert_private']

    ctx.logger.info('Installing RabbitMQ...')
    utils.set_selinux_permissive()

    utils.copy_notice('rabbitmq')
    utils.mkdir(rabbitmq_log_path)

    utils.yum_install(erlang_rpm_source_url)
    utils.yum_install(rabbitmq_rpm_source_url)

    utils.logrotate('rabbitmq')

    # Creating rabbitmq systemd stop script
    utils.deploy_blueprint_resource(
        '{0}/kill-rabbit'.format(CONFIG_PATH),
        '/usr/local/bin/kill-rabbit')
#TODO: create chmod in utils and convert all
    utils.sudo(['chmod', '500', '/usr/local/bin/kill-rabbit'])
    utils.systemd.configure('rabbitmq')

    ctx.logger.info('Configuring File Descriptors Limit...')
    utils.deploy_blueprint_resource(
        '{0}/rabbitmq_ulimit.conf'.format(CONFIG_PATH),
        '/etc/security/limits.d/rabbitmq.conf')

    utils.systemd.systemctl('daemon-reload')

    ctx.logger.info('Chowning RabbitMQ logs path...')
    utils.chown('rabbitmq', 'rabbitmq', rabbitmq_log_path)

    ctx.logger.info('Starting RabbitMQ Server in Daemonized mode...')
    utils.systemd.systemctl('start', service='cloudify-rabbitmq.service')

    sleep(30)

    ctx.logger.info('Enabling RabbitMQ Plugins...')
    # Occasional timing issues with rabbitmq starting have resulted in
    # failures when first trying to enable plugins
    utils.sudo(['rabbitmq-plugins', 'enable', 'rabbitmq_management'],
               retries=5)
    utils.sudo(['rabbitmq-plugins', 'enable', 'rabbitmq_tracing'], retries=5)

    clear_guest_permissions_if_guest_exists()

    create_rabbit_mq_user_and_set_permissions(rabbitmq_username,
                                              rabbitmq_password)

    set_rabbit_mq_security(rabbitmq_ssl_enabled,
                           rabbitmq_cert_private,
                           rabbitmq_cert_public)

    # ctx.logger.info('Stopping RabbitMQ Service...')
    # utils.systemd.systemctl('stop', service='cloudify-rabbitmq.service',
    #                         retries=5)
    # utils.clean_var_log_dir('rabbitmq')

#TODO: put in main
#TODO: all string formats in single quotes

ctx.logger.info('Setting Broker IP runtime property.')
if not ctx.instance.runtime_properties.get('rabbitmq_endpoint_ip'):
    os.putenv('BROKER_IP', ctx.instance.host_ip)
    ctx.logger.info('BROKER_IP={0}'.format(ctx.instance.host_ip))
    install_rabbitmq()
else:
    os.putenv('BROKER_IP', ctx.instance.runtime_properties.get(
            'rabbitmq_endpoint_ip'))
    ctx.logger.info('Using external rabbitmq at {0}'.format(
            ctx.instance.runtime_properties.get('rabbitmq_endpoint_ip')))

ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = \
    os.getenv('BROKER_IP')
ctx.logger.info('RabbitMQ Endpoint IP is: {0}'.format(os.getenv('BROKER_IP')))

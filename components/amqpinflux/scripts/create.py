#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


AMQPINFLUX_HOME = '/opt/amqpinflux'


def _install_optional(amqpinflux_venv):
    amqpinflux_source_url = ctx.node.properties['amqpinflux_module_source_url']
    # this allows to upgrade amqpinflux if necessary.
    if amqpinflux_source_url:
        utils.install_python_package(amqpinflux_source_url, amqpinflux_venv)


def _deploy_broker_configuration(amqpinflux_group):

    rabbitmq_cert_enabled = ctx.node.properties['rabbitmq_ssl_enabled']
    rabbitmq_cert_public = ctx.node.properties['rabbitmq_cert_public']

    if rabbitmq_cert_enabled:
        broker_cert_path = os.path.join(AMQPINFLUX_HOME, 'amqp_pub.pem')
        # If no certificate was supplied, the deploy function will raise
        # an error.
        utils.deploy_ssl_certificate(
            'public', broker_cert_path, amqpinflux_group, rabbitmq_cert_public)
        ctx.instance.runtime_properties['broker_cert_path'] = broker_cert_path
    elif rabbitmq_cert_public is not None:
        ctx.logger.warn('Broker SSL cert supplied but SSL not enabled '
                        '(broker_ssl_enabled is False).')


def install_amqpinflux():

    amqpinflux_rpm_source_url = \
        ctx.node.properties['amqpinflux_rpm_source_url']

    # injected as an input to the script
    ctx.instance.runtime_properties['influxdb_endpoint_ip'] = \
        os.environ['INFLUXDB_ENDPOINT_IP']
    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = \
        utils.get_rabbitmq_endpoint_ip()

    amqpinflux_user = 'amqpinflux'
    amqpinflux_group = 'amqpinflux'
    amqpinflux_venv = '{0}/env'.format(AMQPINFLUX_HOME)

    ctx.logger.info('Installing AQMPInflux...')
    utils.set_selinux_permissive()

    utils.copy_notice('amqpinflux')
    utils.mkdir(AMQPINFLUX_HOME)

    utils.yum_install(amqpinflux_rpm_source_url)
    _install_optional(amqpinflux_venv)
    utils.create_service_user(amqpinflux_user, AMQPINFLUX_HOME)
    _deploy_broker_configuration(amqpinflux_group)

    ctx.logger.info('Fixing permissions...')
    utils.chown(amqpinflux_user, amqpinflux_group, AMQPINFLUX_HOME)

    utils.systemd.configure('amqpinflux')


install_amqpinflux()

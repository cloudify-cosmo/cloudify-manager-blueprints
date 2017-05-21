#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'amqpinflux'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME
AMQPINFLUX_USER = SERVICE_NAME
AMQPINFLUX_GROUP = SERVICE_NAME
runtime_props['service_user'] = AMQPINFLUX_USER
runtime_props['service_group'] = AMQPINFLUX_GROUP

HOME_DIR = join('/opt', SERVICE_NAME)
runtime_props['files_to_remove'] = [HOME_DIR]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)


def _install_optional(amqpinflux_venv):
    ctx.logger.info('Installing optional modules...')
    amqpinflux_source_url = ctx_properties['amqpinflux_module_source_url']
    # this allows to upgrade amqpinflux if necessary.
    if amqpinflux_source_url:
        utils.install_python_package(amqpinflux_source_url, amqpinflux_venv)


def install_amqpinflux():

    amqpinflux_rpm_source_url = \
        ctx_properties['amqpinflux_rpm_source_url']

    # injected as an input to the script
    ctx.instance.runtime_properties['influxdb_endpoint_ip'] = \
        os.environ['INFLUXDB_ENDPOINT_IP']
    rabbit_props = utils.ctx_factory.get('rabbitmq')
    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = \
        utils.get_rabbitmq_endpoint_ip()
    ctx.instance.runtime_properties['rabbitmq_username'] = \
        rabbit_props.get('rabbitmq_username')
    ctx.instance.runtime_properties['rabbitmq_password'] = \
        rabbit_props.get('rabbitmq_password')

    amqpinflux_venv = '{0}/env'.format(HOME_DIR)

    ctx.logger.info('Installing AQMPInflux...')
    utils.set_selinux_permissive()

    utils.copy_notice(SERVICE_NAME)
    utils.mkdir(HOME_DIR)

    utils.yum_install(amqpinflux_rpm_source_url,
                      service_name=SERVICE_NAME)
    _install_optional(amqpinflux_venv)

    ctx.logger.info('Configuring AMQPInflux...')
    utils.create_service_user(AMQPINFLUX_USER, AMQPINFLUX_GROUP, HOME_DIR)
    ctx.instance.runtime_properties['broker_cert_path'] = \
        utils.INTERNAL_CERT_PATH
    utils.chown(AMQPINFLUX_USER, AMQPINFLUX_GROUP, HOME_DIR)
    utils.systemd.configure(SERVICE_NAME)


install_amqpinflux()

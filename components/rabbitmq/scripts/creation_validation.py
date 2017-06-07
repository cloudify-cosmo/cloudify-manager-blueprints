#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties

IMMUTABLE_PROPERTIES = [
    'rabbitmq_username',
    'rabbitmq_password',
    'rabbitmq_endpoint_ip',
    'rabbitmq_cert_public',
    'rabbitmq_cert_private'
]

if utils.is_upgrade:
    SERVICE_NAME = runtime_props['service_name']
    utils.validate_upgrade_directories(SERVICE_NAME)
    utils.verify_immutable_properties(SERVICE_NAME, IMMUTABLE_PROPERTIES)

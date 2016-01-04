#!/usr/bin/env python

import importlib
import os
from subprocess import check_output

utils_path = check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')


config_path = "components/rabbitmq/config"

rabbitmq_endpoint_ip = ctx.node.properties('rabbitmq_endpoint_ip')

if rabbitmq_endpoint_ip == '':
    ctx.logger.info("Starting RabbitMQ Service...")
    utils.systemd.start('cloudify-rabbitmq.service')

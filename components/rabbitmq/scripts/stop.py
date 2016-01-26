#!/usr/bin/env python

from cloudify import ctx

import utils

ctx.logger.info("Stopping RabbitMQ Service...")
utils.systemd.systemctl('stop', service='cloudify-rabbitmq.service')

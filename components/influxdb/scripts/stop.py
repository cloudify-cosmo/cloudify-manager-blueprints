#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


ctx_properties = utils.CtxPropertyFactory().create('influxdb')

INFLUXDB_ENDPOINT_IP = ctx_properties['influxdb_endpoint_ip']

if not INFLUXDB_ENDPOINT_IP:
    ctx.logger.info('Stopping InfluxDB Service...')
    utils.systemd.stop('influxdb')

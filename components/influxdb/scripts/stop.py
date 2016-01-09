#!/usr/bin/env python

from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils

INFLUXDB_ENDPOINT_IP = ctx.node.properties['influxdb_endpoint_ip']

if not INFLUXDB_ENDPOINT_IP:
    ctx.logger.info('Stopping InfluxDB Service...')
    utils.systemd.stop('influxdb')

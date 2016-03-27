#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


INFLUXDB_ENDPOINT_IP = ctx.node.properties['influxdb_endpoint_ip']

if not INFLUXDB_ENDPOINT_IP:
    utils.systemd.stop('cloudify-influxdb.service')

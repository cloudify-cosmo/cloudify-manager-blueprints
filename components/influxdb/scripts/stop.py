#!/usr/bin/env python

import subprocess
import os
import importlib

subprocess.check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')

INFLUXDB_ENDPOINT_IP = ctx.node.properties('influxdb_endpoint_ip')

if not INFLUXDB_ENDPOINT_IP:
    ctx.logger.info('Starting InfluxDB Service...')
    utils.systemd.stop('influxdb')

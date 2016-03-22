#!/usr/bin/env python

from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils

ES_ENDPOINT_IP = ctx.node.properties['es_endpoint_ip']

if not ES_ENDPOINT_IP:
    ctx.logger.info('Starting Elasticsearch Service...')
    utils.systemd.start('elasticsearch')

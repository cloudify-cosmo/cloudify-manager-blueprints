#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA
ES_SERVICE_NAME = 'elasticsearch'

ctx_properties = utils.ctx_factory.get(ES_SERVICE_NAME)
ES_ENDPOINT_IP = ctx_properties.get('es_endpoint_ip')

if not ES_ENDPOINT_IP:
    ctx.logger.info('Starting Elasticsearch Service...')
    utils.start_service(ES_SERVICE_NAME, append_prefix=False)

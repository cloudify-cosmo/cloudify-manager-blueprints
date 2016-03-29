#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

ctx_properties = utils.CtxPropertyFactory().create('elasticsearch',
                                                   write_to_file=False)
ES_ENDPOINT_IP = ctx_properties['es_endpoint_ip']

if not ES_ENDPOINT_IP:
    ctx.logger.info('Starting Elasticsearch Service...')
    utils.start_service_and_archive_properties('elasticsearch')

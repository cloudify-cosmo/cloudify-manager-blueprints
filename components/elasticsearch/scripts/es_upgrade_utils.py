#!/usr/bin/env python

"""This script is used to migrate elements between
versions upon manager inplace upgrade/rollback. The data elements migrated
by this script are 'provider_context' and 'snapshot' element types.
"""

import os
import json
from cloudify import ctx
from os.path import join, dirname

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

DUMP_FILE_PATH = os.path.join(utils.ES_UPGRADE_DUMP_PATH, 'es_dump')
DUMP_SUCCESS_FLAG = os.path.join(utils.ES_UPGRADE_DUMP_PATH, 'es_dump_success')


def restore_upgrade_data(es_endpoint_ip, es_endpoint_port):
    bulk_endpoint = 'http://{0}:{1}/_bulk'.format(es_endpoint_ip,
                                                  es_endpoint_port)
    all_data = ''
    with open(DUMP_FILE_PATH) as f:
        for line in f:
            element = _update_element_if_required(json.loads(line))
            all_data += _create_element_request(element)
    ctx.logger.info('Restoring elasticsearch data')
    res = utils.http_request(url=bulk_endpoint, data=all_data, method='POST')
    if not res.code == 200:
        ctx.abort_operation('Failed restoring elasticsearch data.')
    ctx.logger.info('Elasticsearch data was successfully restored')


def dump_upgrade_data():

    if os.path.exists(DUMP_SUCCESS_FLAG):
        return

    endpoint = _get_es_install_endpoint()
    port = _get_es_install_port()
    storage_endpoint = 'http://{0}:{1}/cloudify_storage'.format(endpoint,
                                                                port)
    types = ['provider_context', 'snapshot']
    ctx.logger.info('Dumping upgrade data: {0}'.format(types))
    type_values = []
    for _type in types:
        res = utils.http_request('{0}/_search?q=_type:{1}&size=10000'
                                 .format(storage_endpoint, _type),
                                 method='GET')
        if not res.code == 200:
            ctx.abort_operation('Failed fetching type {0} from '
                                'cloudify_storage index'.format(_type))

        body = res.read()
        hits = json.loads(body)['hits']['hits']
        for hit in hits:
            type_values.append(hit)

    utils.mkdir(utils.ES_UPGRADE_DUMP_PATH)
    with open(DUMP_FILE_PATH, 'w') as f:
        for item in type_values:
            f.write(json.dumps(item) + os.linesep)

    # marker file to indicate dump has succeeded
    with open(DUMP_SUCCESS_FLAG, 'w') as f:
        f.write('success')


def _update_element_if_required(element):
    # Manager versions above 3.4.0 must contain a 'broker_ip' property in the
    # agent configuration
    if element['_type'] == 'provider_context':
        content = element['_source']
        agent_conf = content['context']['cloudify']['cloudify_agent']
        if not agent_conf.get('broker_ip') and utils.is_upgrade:
            agent_conf['broker_ip'] = \
                ctx.instance.runtime_properties['broker_ip']
    return element


def _create_element_request(element):
    source = json.dumps(element['_source'])
    metadata = _only_types(element, ['_type', '_id', '_index'])
    action_and_meta_data = json.dumps({'index': metadata})
    return action_and_meta_data + os.linesep + source + os.linesep


def _get_es_install_port():
    es_props = utils.ctx_factory.load_rollback_props('elasticsearch')
    return es_props['es_endpoint_port']


def _get_es_install_endpoint():
    es_props = utils.ctx_factory.load_rollback_props('elasticsearch')
    if es_props['es_endpoint_ip']:
        es_endpoint = es_props['es_endpoint_ip']
    else:
        es_endpoint = ctx.instance.host_ip
    return es_endpoint


def _only_types(d, args):
    return {key: d[key] for key in d.keys() if key in args}

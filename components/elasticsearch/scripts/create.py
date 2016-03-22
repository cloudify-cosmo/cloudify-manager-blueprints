#!/usr/bin/env python

import os
import urllib2
import json
import time
from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils

CONFIG_PATH = "components/elasticsearch/config"


def http_request(url, data=None, method='PUT'):
    request = urllib2.Request(url, data=data)
    request.get_method = lambda: method
    try:
        urllib2.urlopen(request)
        return True
    except urllib2.URLError as e:
        reqstring = url + (' ' + data if data else '')
        ctx.logger.info('Failed to {0} {1} (reason: {2})'.format(
            method, reqstring, e.reason))


def configure_elasticsearch(host, port):

    storage_endpoint = 'http://{0}:{1}/cloudify_storage/'.format(host, port)
    storage_settings = json.dumps({
        "settings": {
            "analysis": {
                "analyzer": {
                    "default": {"tokenizer": "whitespace"}
                }
            }
        }
    })

    ctx.logger.info('Deleting `cloudify_storage` index if exists...')
    http_request(storage_endpoint, method='DELETE')
    ctx.logger.info('Creating `cloudify_storage` index...')
    http_request(storage_endpoint, storage_settings, 'PUT')

    blueprint_mapping_endpoint = storage_endpoint + 'blueprint/_mapping'
    blueprint_mapping = json.dumps({
        "blueprint": {
            "properties": {
                "plan": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring blueprint mapping...')
    http_request(blueprint_mapping_endpoint, blueprint_mapping, 'PUT')

    deployment_mapping_endpoint = storage_endpoint + 'deployment/_mapping'
    deployment_mapping = json.dumps({
        "deployment": {
            "properties": {
                "workflows": {"enabled": False},
                "inputs": {"enabled": False},
                "policy_type": {"enabled": False},
                "policy_triggers": {"enabled": False},
                "groups": {"enabled": False},
                "outputs": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring deployment mapping...')
    http_request(deployment_mapping_endpoint, deployment_mapping, 'PUT')

    node_mapping_endpoint = storage_endpoint + 'node/_mapping'
    node_mapping = json.dumps({
        "node": {
            "_id": {"path": "id"},
            "properties": {
                "types": {"type": "string", "index_name": "type"},
                "properties": {"enabled": False},
                "operations": {"enabled": False},
                "relationships": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring node mapping...')
    http_request(node_mapping_endpoint, node_mapping, 'PUT')

    node_instance_mapping_endpoint = \
        storage_endpoint + 'node_instance/_mapping'
    node_instance_mapping = json.dumps({
        "node_instance": {
            "_id": {"path": "id"},
            "properties": {
                "runtime_properties": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring node instance mapping...')
    http_request(node_instance_mapping_endpoint, node_instance_mapping, 'PUT')

    deployment_modification_mapping_endpoint = \
        storage_endpoint + 'deployment_modification/_mapping'
    deployment_modification_mapping = json.dumps({
        "deployment_modification": {
            "_id": {"path": "id"},
            "properties": {
                "modified_nodes": {"enabled": False},
                "node_instances": {"enabled": False},
                "context": {"enabled": False}
            }
        }
    })

    ctx.logger.info('Declaring deployment modification mapping...')
    http_request(
        deployment_modification_mapping_endpoint,
        deployment_modification_mapping, 'PUT')


def install_elasticsearch():
    es_java_opts = ctx.node.properties['es_java_opts']
    es_heap_size = ctx.node.properties['es_heap_size']

    es_source_url = ctx.node.properties['es_rpm_source_url']
    es_curator_rpm_source_url = \
        ctx.node.properties['es_curator_rpm_source_url']

    # this will be used only if elasticsearch-curator is not installed via
    # an rpm and an internet connection is available
    es_curator_version = "3.2.3"

    es_home = "/opt/elasticsearch"
    es_logs_path = "/var/log/cloudify/elasticsearch"
    es_conf_path = "/etc/elasticsearch"
    es_unit_override = "/etc/systemd/system/elasticsearch.service.d"

    ctx.logger.info('Installing Elasticsearch...')
    utils.set_selinux_permissive()

    utils.copy_notice('elasticsearch')
    utils.mkdir(es_home)
    utils.mkdir(es_logs_path)

    utils.yum_install(es_source_url)

    ctx.logger.info('Chowning {0} by elasticsearch user...'.format(
        es_logs_path))
    utils.chown('elasticsearch', 'elasticsearch', es_logs_path)

    ctx.logger.info('Creating systemd unit override...')
    utils.mkdir(es_unit_override)
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'restart.conf'),
        os.path.join(es_unit_override, 'restart.conf'))

    ctx.logger.info('Deploying Elasticsearch Configuration...')
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'elasticsearch.yml'),
        os.path.join(es_conf_path, 'elasticsearch.yml'))
    utils.chown('elasticsearch', 'elasticsearch',
                os.path.join(es_conf_path, 'elasticsearch.yml'))

    ctx.logger.info('Deploying elasticsearch logging configuration file...')
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'logging.yml'),
        os.path.join(es_conf_path, 'logging.yml'))
    utils.chown('elasticsearch', 'elasticsearch',
                os.path.join(es_conf_path, 'logging.yml'))

    ctx.logger.info('Setting Elasticsearch Heap Size...')
    # we should treat these as templates.
    utils.replace_in_file(
        '#ES_HEAP_SIZE=2g',
        'ES_HEAP_SIZE={0}'.format(es_heap_size),
        '/etc/sysconfig/elasticsearch')

    if es_java_opts:
        ctx.logger.info('Setting additional JAVA_OPTS...')
        utils.replace_in_file(
            '#ES_JAVA_OPTS',
            'ES_JAVA_OPTS={0}'.format(es_java_opts),
            '/etc/sysconfig/elasticsearch')

    ctx.logger.info('Setting Elasticsearch logs path...')
    utils.replace_in_file(
        '#LOG_DIR=/var/log/elasticsearch',
        'LOG_DIR={0}'.format(es_logs_path),
        '/etc/sysconfig/elasticsearch')
    utils.replace_in_file(
        '#ES_GC_LOG_FILE=/var/log/elasticsearch/gc.log',
        'ES_GC_LOG_FILE={0}'.format(os.path.join(es_logs_path, 'gc.log')),
        '/etc/sysconfig/elasticsearch')
    utils.logrotate('elasticsearch')

    ctx.logger.info('Installing Elasticsearch Curator...')
    if not es_curator_rpm_source_url:
        ctx.install_python_package('elasticsearch-curator=={0}'.format(
            es_curator_version))
    else:
        utils.yum_install(es_curator_rpm_source_url)

    rotator_script = ctx.download_resource(
        'components/elasticsearch/scripts/rotate_es_indices')
    ctx.logger.info('Configuring Elasticsearch Index Rotation cronjob for '
                    'logstash-YYYY.mm.dd index patterns...')

    # testable manually by running: sudo run-parts /etc/cron.daily
    utils.move(rotator_script, '/etc/cron.daily/rotate_es_indices')
    utils.chown('root', 'root', '/etc/cron.daily/rotate_es_indices')
    # VALIDATE!
    utils.sudo('chmod +x /etc/cron.daily/rotate_es_indices')

    ctx.logger.info('Enabling Elasticsearch Service...')
    utils.systemd.enable('elasticsearch.service')


def main():

    es_endpoint_ip = ctx.node.properties['es_endpoint_ip']
    es_endpoint_port = ctx.node.properties['es_endpoint_port']

    if not es_endpoint_ip:
        es_endpoint_ip = ctx.instance.host_ip
        install_elasticsearch()

        ctx.logger.info('Starting Elasticsearch Service...')
        utils.systemd.start('elasticsearch.service')
        utils.wait_for_port(es_endpoint_port, es_endpoint_ip)
        configure_elasticsearch(host=es_endpoint_ip, port=es_endpoint_port)

        ctx.logger.info('Stopping Elasticsearch Service...')
        utils.systemd.stop('elasticsearch.service')
        utils.clean_var_log_dir('elasticsearch')
    else:
        ctx.logger.info('External Elasticsearch Endpoint provided: '
                        '{0}:{1}...'.format(es_endpoint_ip, es_endpoint_port))
        time.sleep(5)
        utils.wait_for_port(es_endpoint_port, es_endpoint_ip)
        ctx.logger.info('Checking if \'cloudify_storage\' '
                        'index already exists...')

        if http_request('http://{0}:{1}/cloudify_storage'.format(
                es_endpoint_ip, es_endpoint_port), method='HEAD'):
            utils.error_exit('\'cloudify_storage\' index already exists on '
                             '{0}, terminating bootstrap...'.format(
                                 es_endpoint_ip))
        configure_elasticsearch(host=es_endpoint_ip, port=es_endpoint_port)

    ctx.instance.runtime_properties['es_endpoint_ip'] = es_endpoint_ip


main()

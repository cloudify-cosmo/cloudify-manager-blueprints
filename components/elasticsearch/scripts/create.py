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

ES_JAVA_OPTS = ctx.node.properties('es_java_opts')
ES_HEAP_SIZE = ctx.node.properties('es_heap_size')
ES_ENDPOINT_IP = ctx.node.properties('es_endpoint_ip')
ES_ENDPOINT_PORT = ctx.node.properties('es_endpoint_port')

ES_SOURCE_URL = ctx.node.properties('es_rpm_source_url')
ES_CURATOR_RPM_SOURCE_URL = ctx.node.properties('es_curator_rpm_source_url')

# this will be used only if elasticsearch-curator is not installed via an rpm
ES_CURATOR_VERSION = "3.2.3"

ES_HOME = "/opt/elasticsearch"
ES_LOGS_PATH = "/var/log/cloudify/elasticsearch"
ES_CONF_PATH = "/etc/elasticsearch"
ES_UNIT_OVERRIDE = "/etc/systemd/system/elasticsearch.service.d"


def http_request(url, data=None, method='PUT'):
    request = urllib2.Request(url, data=data)
    request.get_method = lambda: method
    try:
        urllib2.urlopen(request)
        return True
    except urllib2.URLError as e:
        ctx.logger.info('Failed {0} to {1} (code: {2}, reason: {3})'.format(
            method, url + ' ' + data, e.reason[0], e.reason[1]))


def configure_elasticsearch(host=ES_ENDPOINT_PORT, port=ES_ENDPOINT_IP):

    storage_endpoint = 'http://{0}:{1}/cloudify_storage/'
    storage_settings = json.dumps({
        "settings": {
            "analysis": {
                "analyzer": {
                    "default": {"tokenizer": "whitespace"}
                }
            }
        }
    })

    http_request(storage_endpoint, method='DELETE')
    http_request(storage_endpoint, storage_settings, 'PUT')

    blueprint_mapping_endpoint = storage_endpoint + 'blueprint/_mapping'
    blueprint_mapping = json.dumps({
        "blueprint": {
            "properties": {
                "plan": {"enabled": False}
            }
        }
    })

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

    http_request(
        deployment_modification_mapping_endpoint,
        deployment_modification_mapping, 'PUT')


def install_elasticsearch():
    ctx.logger.info('Installing Elasticsearch...')
    utils.set_selinux_permissive()

    utils.copy_notice('elasticsearch')
    utils.create_dir(ES_HOME)
    utils.create_dir(ES_LOGS_PATH)

    utils.yum_install(ES_SOURCE_URL)

    ctx.logger.info('Chowning {0} by elasticsearch user...'.format(
        ES_LOGS_PATH))
    utils.chown('elasticsearch', 'elasticsearch', ES_LOGS_PATH)

    ctx.logger.info('Creating systemd unit override...')
    utils.create_dir(ES_UNIT_OVERRIDE)
    ctx.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'restart.conf'),
        os.path.join(ES_UNIT_OVERRIDE, 'restart.conf'))

    ctx.logger.info('Deploying Elasticsearch Configuration...')
    ctx.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'elasticsearch.yml'),
        os.path.join(ES_CONF_PATH, 'elasticsearch.yml'))
    utils.chown('elasticsearch', 'elasticsearch',
                os.path.join(ES_CONF_PATH, 'elasticsearch.yml'))

    ctx.logger.info('Deploying elasticsearch logging configuration file...')
    ctx.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'logging.yml'),
        os.path.join(ES_CONF_PATH, 'logging.yml'))
    utils.chown('elasticsearch', 'elasticsearch',
                os.path.join(ES_CONF_PATH, 'logging.yml'))

    ctx.logger.info('Setting Elasticsearch Heap Size...')
    # we should treat these as templates.
    utils.replace_in_file(
        '#ES_HEAP_SIZE=2g',
        'ES_HEAP_SIZE={0}'.format(ES_HEAP_SIZE),
        '/etc/sysconfig/elasticsearch')

    if ES_JAVA_OPTS:
        ctx.logger.info('Setting additional JAVA_OPTS...')
        utils.replace_in_file(
            '#ES_JAVA_OPTS',
            'ES_JAVA_OPTS={0}'.format(ES_JAVA_OPTS),
            '/etc/sysconfig/elasticsearch')

    ctx.logger.info('Setting Elasticsearch logs path...')
    utils.replace_in_file(
        '#LOG_DIR=/var/log/elasticsearch',
        'LOG_DIR={0}'.format(ES_LOGS_PATH),
        '/etc/sysconfig/elasticsearch')
    utils.replace_in_file(
        '#ES_GC_LOG_FILE=/var/log/elasticsearch/gc.log',
        'ES_GC_LOG_FILE={0}'.format(os.path.join(ES_LOGS_PATH, 'gc.log')),
        '/etc/sysconfig/elasticsearch')
    utils.deploy_logrotate_config('elasticsearch')

    ctx.logger.info('Installing Elasticsearch Curator...')
    if not ES_CURATOR_RPM_SOURCE_URL:
        ctx.install_python_package('elasticsearch-curator=={0}'.format(
            ES_CURATOR_VERSION))
    else:
        utils.yum_install(ES_CURATOR_RPM_SOURCE_URL)

    rotator_script = ctx.download_resource(
        'components/elasticsearch/scripts/rotate_es_indices')
    ctx.logger.info('Configuring Elasticsearch Index Rotation cronjob for '
                    'logstash-YYYY.mm.dd index patterns...')

    # testable manually by running: sudo run-parts /etc/cron.daily
    utils.move(rotator_script, '/etc/cron.daily/rotate_es_indices')
    utils.chown('root', 'root', '/etc/cron.daily/rotate_es_indices')
    utils.sudo('chmod +x /etc/cron.daily/rotate_es_indices')

    ctx.logger.info('Enabling Elasticsearch Service...')
    utils.systemd.enable('elasticsearch.service')


if not ES_ENDPOINT_IP:
    ES_ENDPOINT_IP = ctx.instance.host_ip()
    install_elasticsearch()

    ctx.logger.info('Starting Elasticsearch Service...')
    utils.systemd.start('elasticsearch.service')
    utils.wait_for_port(ES_ENDPOINT_PORT, ES_ENDPOINT_IP)
    configure_elasticsearch(host=ES_ENDPOINT_IP)

    ctx.logger.info('Stopping Elasticsearch Service...')
    utils.systemd.stop('elasticsearch.service')
    utils.clean_var_log_dir('elasticsearch')
else:
    ctx.logger.info('External Elasticsearch Endpoint provided: '
                    '{0}:{1}...'.format(ES_ENDPOINT_IP, ES_ENDPOINT_PORT))
    time.sleep(5)
    utils.wait_for_port(ES_ENDPOINT_PORT, ES_ENDPOINT_IP)
    ctx.logger.info('Checking if \'cloudify_storage\' index already exists...')

    if http_request('http://{0}:{1}/cloudify_storage'.format(
            ES_ENDPOINT_IP, ES_ENDPOINT_PORT), method='HEAD'):
        utils.error_exit('\'cloudify_storage\' index already exists on {0}, '
                         'terminating bootstrap...'.format(ES_ENDPOINT_IP))
    configure_elasticsearch()

ctx.instance.runtime_properties('es_endpoint_ip', ES_ENDPOINT_IP)

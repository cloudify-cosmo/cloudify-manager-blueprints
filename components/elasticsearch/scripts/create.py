#!/usr/bin/env python

import os
import urllib2
import json
import time
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

ctx.download_resource(
    join('components', 'elasticsearch', 'scripts', 'es_upgrade_utils.py'),
    join(dirname(__file__), 'es_upgrade_utils.py'))
import es_upgrade_utils  # NOQA


CONFIG_PATH = "components/elasticsearch/config"
ES_SERVICE_NAME = 'elasticsearch'

ctx_properties = utils.ctx_factory.create(ES_SERVICE_NAME)


def _configure_elasticsearch(host, port):

    ctx.logger.info('Configuring Elasticsearch storage index...')
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

    ctx.logger.debug('Deleting `cloudify_storage` index if exists...')
    if utils.http_request(storage_endpoint, method='GET'):
        utils.http_request(storage_endpoint, method='DELETE')

    ctx.logger.debug('Creating `cloudify_storage` index...')
    utils.http_request(storage_endpoint, storage_settings, 'PUT')


def _configure_index_rotation():
    ctx.logger.info('Configurating index rotation...')
    ctx.logger.debug(
        'Setting up curator rotation cronjob for logstash-YYYY.mm.dd '
        'index patterns...')
    utils.deploy_blueprint_resource(
        'components/elasticsearch/scripts/rotate_es_indices',
        '/etc/cron.daily/rotate_es_indices', ES_SERVICE_NAME)
    utils.chown('root', 'root', '/etc/cron.daily/rotate_es_indices')
    # TODO: VALIDATE!
    # TODO: use utils.chmod
    utils.sudo('chmod +x /etc/cron.daily/rotate_es_indices')


def _install_elasticsearch():
    es_java_opts = ctx_properties['es_java_opts']
    es_heap_size = ctx_properties['es_heap_size']

    es_source_url = ctx_properties['es_rpm_source_url']
    es_curator_rpm_source_url = \
        ctx_properties['es_curator_rpm_source_url']

    # this will be used only if elasticsearch-curator is not installed via
    # an rpm and an internet connection is available
    es_curator_version = "3.2.3"

    es_home = "/opt/elasticsearch"
    es_logs_path = "/var/log/cloudify/elasticsearch"
    es_conf_path = "/etc/elasticsearch"
    es_unit_override = "/etc/systemd/system/elasticsearch.service.d"
    es_scripts_path = os.path.join(es_conf_path, 'scripts')

    ctx.logger.info('Installing Elasticsearch...')
    utils.set_selinux_permissive()

    utils.copy_notice('elasticsearch')
    utils.mkdir(es_home)
    utils.mkdir(es_logs_path)

    utils.yum_install(es_source_url, service_name=ES_SERVICE_NAME)

    ctx.logger.info('Configuring Elasticsearch...')
    utils.chown('elasticsearch', 'elasticsearch', es_logs_path)

    ctx.logger.debug('Creating systemd unit override...')
    utils.mkdir(es_unit_override)
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'restart.conf'),
        os.path.join(es_unit_override, 'restart.conf'), ES_SERVICE_NAME)

    ctx.logger.debug('Deploying Elasticsearch configuration file...')
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'elasticsearch.yml'),
        os.path.join(es_conf_path, 'elasticsearch.yml'), ES_SERVICE_NAME)
    utils.chown('elasticsearch', 'elasticsearch',
                os.path.join(es_conf_path, 'elasticsearch.yml'))

    ctx.logger.debug(
        'Deploying elasticsearch logging configuration file...')
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'logging.yml'),
        os.path.join(es_conf_path, 'logging.yml'), ES_SERVICE_NAME)
    utils.chown('elasticsearch', 'elasticsearch',
                os.path.join(es_conf_path, 'logging.yml'))

    ctx.logger.debug('Creating Elasticsearch scripts folder and '
                     'additional external Elasticsearch scripts...')
    utils.mkdir(es_scripts_path)
    utils.deploy_blueprint_resource(
        os.path.join(CONFIG_PATH, 'scripts', 'append.groovy'),
        os.path.join(es_scripts_path, 'append.groovy'),
        ES_SERVICE_NAME
    )

    ctx.logger.debug('Setting Elasticsearch Heap Size...')
    # we should treat these as templates.
    utils.replace_in_file(
        '(?:#|)ES_HEAP_SIZE=(.*)',
        'ES_HEAP_SIZE={0}'.format(es_heap_size),
        '/etc/sysconfig/elasticsearch')

    if es_java_opts:
        ctx.logger.debug('Setting additional JAVA_OPTS...')
        utils.replace_in_file(
            '(?:#|)ES_JAVA_OPTS=(.*)',
            'ES_JAVA_OPTS={0}'.format(es_java_opts),
            '/etc/sysconfig/elasticsearch')

    ctx.logger.debug('Setting Elasticsearch logs path...')
    utils.replace_in_file(
        '(?:#|)LOG_DIR=(.*)',
        'LOG_DIR={0}'.format(es_logs_path),
        '/etc/sysconfig/elasticsearch')
    utils.replace_in_file(
        '(?:#|)ES_GC_LOG_FILE=(.*)',
        'ES_GC_LOG_FILE={0}'.format(os.path.join(es_logs_path, 'gc.log')),
        '/etc/sysconfig/elasticsearch')
    utils.logrotate(ES_SERVICE_NAME)

    ctx.logger.info('Installing Elasticsearch Curator...')
    if not es_curator_rpm_source_url:
        ctx.install_python_package('elasticsearch-curator=={0}'.format(
            es_curator_version))
    else:
        utils.yum_install(es_curator_rpm_source_url,
                          service_name=ES_SERVICE_NAME)

    _configure_index_rotation()

    # elasticsearch provides a systemd init env. we just enable it.
    utils.systemd.enable(ES_SERVICE_NAME, append_prefix=False)


def _wait_for_shards(port, ip):
    """Wait for activation of all available shards in Elasticsearch.

    After Elasticsearch is installed and first time started there is short time
    when shards, if created, are not started. If someone would access ES during
    that time (e.g. by creating snapshot) he will get error
    'SearchPhaseExecutionException[Failed to execute phase [init_scan], all
    shards failed]'.

    :param port: Elasticsearch port
    :param ip: Ip to Elasticsearch
    """
    ctx.logger.info('Waiting for shards to be active...')
    shards_check_timeout = 60
    start = time.time()

    url = 'http://{ip}:{port}/*/_search_shards'.format(ip=ip, port=port)
    while True:
        all_shards_started = True
        try:
            out = urllib2.urlopen(url)
            shards = json.load(out)['shards']
            for shard in shards:
                all_shards_started = all_shards_started and \
                    (shard[0]['state'] == 'STARTED')
        except urllib2.URLError as e:
            ctx.abort_operation('Failed to retrieve information about '
                                'Elasticsearch shards: {0}'.format(e.reason))

        if all_shards_started:
            return
        time.sleep(1)
        if time.time() - start > shards_check_timeout:
            inactive = [s[0] for s in shards if s[0]['state'] != 'STARTED']
            ctx.abort_operation('Elasticsearch shards check timed out. '
                                'Inactive shards: {0}'.format(inactive))


def main():

    es_endpoint_ip = ctx_properties['es_endpoint_ip']
    es_endpoint_port = ctx_properties['es_endpoint_port']

    if utils.is_upgrade or utils.is_rollback:
        # 'provider_context' and 'snapshot' elements will be migrated to the
        # future version
        es_upgrade_utils.dump_upgrade_data()

    if not es_endpoint_ip:
        es_endpoint_ip = ctx.instance.host_ip
        _install_elasticsearch()
        utils.systemd.restart(ES_SERVICE_NAME, append_prefix=False)
        utils.wait_for_port(es_endpoint_port, es_endpoint_ip)
        _configure_elasticsearch(host=es_endpoint_ip, port=es_endpoint_port)
        _wait_for_shards(es_endpoint_port, es_endpoint_ip)

        utils.clean_var_log_dir('elasticsearch')
    else:
        ctx.logger.info('External Elasticsearch Endpoint provided: '
                        '{0}:{1}...'.format(es_endpoint_ip, es_endpoint_port))
        time.sleep(5)
        utils.wait_for_port(es_endpoint_port, es_endpoint_ip)
        ctx.logger.info("Checking if 'cloudify_storage' "
                        "index already exists...")

        if utils.http_request('http://{0}:{1}/cloudify_storage'.format(
                es_endpoint_ip, es_endpoint_port), method='HEAD').code == 200:
            ctx.abort_operation('\'cloudify_storage\' index already exists on '
                                '{0}, terminating bootstrap...'.format(
                                    es_endpoint_ip))
        _configure_elasticsearch(host=es_endpoint_ip, port=es_endpoint_port)

    if not es_endpoint_port:
        utils.systemd.stop(ES_SERVICE_NAME, append_prefix=False)

    ctx.instance.runtime_properties['es_endpoint_ip'] = es_endpoint_ip


main()

#!/bin/bash -e

ELASTICSEARCH_VERSION="1.4.3"
ELASTICSEARCH_HOME="/opt/elasticsearch"
ELASTICSEARCH_LOG_PATH="/var/log/cloudify/elasticsearch"
# ES_JAVA_OPRT=$(ctx node properties es_java_opts)
ES_JAVA_OPTS="-Xmx1024m -Xms1024m"
# ELASTICSEARCH_PORT=$(ctx node properties port)
ELASTICSEARCH_PORT="9200"
# ELASTICSEARCH_DISCOVERY_PORT=$(ctx node properties discovery_port)
ELASTICSEARCH_DISCOVERY_PORT="54329"
# ELASTICHSEARCH_SOURCE_URL=$(ctx node properties elasticsearch_tar_source_url)
ELASTICHSEARCH_SOURCE_URL="https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz"


function import_helpers
{
    if [ ! -e "/tmp/utils" ]; then
        cp components/utils /tmp/utils
        # ctx download-resource "components/utils" '@{"target_path": "/tmp/utils"}'
    fi
    . /tmp/utils

    # ctx download-resource components/elasticsearch/scripts/configure_es '@{"target_path": "/tmp/configure_es"}'
    cp components/elasticsearch/scripts/configure_es /tmp/configure_es
    . /tmp/configure_es

    # required only in current vagrant environment otherwise passed to the vm via the script plugin
    . components/env_vars
}

function main
{

    ctx logger info "Installing Elasticsearch..."

    copy_notice "elasticsearch"
    create_dir ${ELASTICSEARCH_HOME} && \
    create_dir ${ELASTICSEARCH_HOME}/scripts && \
    create_dir ${ELASTICSEARCH_LOG_PATH} && \

    # elasticsearch_installer_source=$(ctx node properties elasticsearch_source_url)
    download_file ${ELASTICHSEARCH_SOURCE_URL} "/tmp/elasticsearch.tar.gz" && \
    ctx logger info "Extracting Elasticsearch..."
    sudo tar -C ${ELASTICSEARCH_HOME}/ -xvf /tmp/elasticsearch.tar.gz --strip-components=1 && \
    clean_tmp

    ctx logger info "Deploying Elasticsearch Config file..."
    # ctx download-resource components/elasticsearch/config/elasticsearch.yml '@{"target_path": "/tmp/elasticsearch.yml"}'
    cp "components/elasticsearch/config/elasticsearch.yml" "/tmp/elasticsearch.yml" && \
    sudo mv "/tmp/elasticsearch.yml" "${ELASTICSEARCH_HOME}/config/elasticsearch.yml" && \
    # sudo sed -i 's|54329|${es_discovery_port}|g' "${ELASTICSEARCH_HOME}/config/elasticsearch.yml"
    ctx logger info "Starting Elasticsearch for configuration purposes..."
    sudo ${ELASTICSEARCH_HOME}/bin/elasticsearch -d && \
    ctx logger info "Waiting for Elasticsearch to become available..."
    wait_for_port "${ELASTICSEARCH_PORT}"
    ctx logger info "Configuring Elasticsearch Indices, Mappings, etc..."
    configure_elasticsearch && \

    ctx logger info "Killing Elasticsearch..."
    sudo pkill -f elasticsearch
}

cd /vagrant
import_helpers
main
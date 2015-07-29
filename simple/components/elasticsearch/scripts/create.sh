#!/bin/bash -e

. $(ctx download-resource "components/utils")
. $(ctx download-resource "components/elasticsearch/scripts/configure_es")


CONFIG_REL_PATH="components/elasticsearch/config"

export ES_JAVA_OPRT=$(ctx node properties es_java_opts)  # (e.g. "-Xmx1024m -Xms1024m")
export ES_JAVA_OPTS=$(ctx node properties es_java_opts)  # (e.g. "-Xmx1024m -Xms1024m")
export ES_HEAP_SIZE=$(ctx node properties es_heap_size)

export ELASTICHSEARCH_SOURCE_URL=$(ctx node properties es_rpm_source_url)  # (e.g. "https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.3.tar.gz")

export ELASTICSEARCH_PORT="9200"
export ELASTICSEARCH_HOME="/opt/elasticsearch"
export ELASTICSEARCH_LOG_PATH="/var/log/cloudify/elasticsearch"
export ELASTICSEARCH_CONF_PATH="/etc/elasticsearch"


ctx logger info "Installing Elasticsearch..."

copy_notice "elasticsearch"
create_dir ${ELASTICSEARCH_HOME}
create_dir ${ELASTICSEARCH_LOG_PATH}

yum_install ${ELASTICHSEARCH_SOURCE_URL}


# we can't use inject_service_env_var from utils as the elasticsearch systemd vars file is not provided by us.
ctx logger info "Setting Elasticsearch Heap size..."
if [ ! -z "${ES_JAVA_OPTS}" ]; then
    replace "#ES_HEAP_SIZE=2g" "ES_HEAP_SIZE=${ES_HEAP_SIZE}" "/etc/sysconfig/elasticsearch"
else
    replace "#ES_HEAP_SIZE=2g" "ES_HEAP_SIZE=1g" "/etc/sysconfig/elasticsearch"
fi

ctx logger info "Setting additional Java OPTS..."
if [ ! -z "${ES_JAVA_OPTS}" ]; then
    replace "#ES_JAVA_OPTS=" "ES_JAVA_OPTS=${ES_JAVA_OPTS}" "/etc/sysconfig/elasticsearch"
fi

ctx logger info "Deploying Elasticsearch Configuration..."
deploy_file "${CONFIG_REL_PATH}/elasticsearch.yml" "${ELASTICSEARCH_CONF_PATH}/elasticsearch.yml"

ctx logger info "Starting Elasticsearch for configuration purposes..."
sudo systemctl enable elasticsearch.service &>/dev/null
sudo systemctl start elasticsearch.service

ctx logger info "Waiting for Elasticsearch to become available..."
wait_for_port "${ELASTICSEARCH_PORT}"

ctx logger info "Configuring Elasticsearch Indices, Mappings, etc..."
# per a function in configure_es
configure_elasticsearch

ctx logger info "Stopping Elasticsearch Service..."
sudo systemctl stop elasticsearch.service

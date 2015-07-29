#!/bin/bash -e

. $(ctx download-resource "components/utils")
. $(ctx download-resource "components/elasticsearch/scripts/configure_es")


CONFIG_REL_PATH="components/elasticsearch/config"

export ES_JAVA_OPRT=$(ctx node properties es_java_opts)  # (e.g. "-Xmx1024m -Xms1024m")
export ELASTICHSEARCH_SOURCE_URL=$(ctx node properties es_rpm_source_url)  # (e.g. "https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.3.tar.gz")

export ELASTICSEARCH_PORT="9200"
export ELASTICSEARCH_HOME="/opt/elasticsearch"
export ELASTICSEARCH_LOG_PATH="/var/log/elasticsearch"
export ELASTICSEARCH_CONF_PATH="/etc/elasticsearch"


ctx logger info "Installing Elasticsearch..."

copy_notice "elasticsearch"
create_dir ${ELASTICSEARCH_HOME}
create_dir ${ELASTICSEARCH_LOG_PATH}

yum_install ${ELASTICHSEARCH_SOURCE_URL}

ctx logger info "Deploying Elasticsearch Configuration..."
deploy_file "${CONFIG_REL_PATH}/elasticsearch.yml" "${ELASTICSEARCH_CONF_PATH}/elasticsearch.yml"

ctx logger info "Deploying Elasticsearch Logging Configuration file..."
deploy_file "${CONFIG_REL_PATH}/logging.yml" "${ELASTICSEARCH_CONF_PATH}/logging.yml"

# ctx logger info "Deploying Elasticsearch Config file..."
# tmp_es_conf_path=$(ctx download-resource "components/elasticsearch/config/elasticsearch.yml")
# sudo mv ${tmp_es_conf_path} "${ELASTICSEARCH_CONF_PATH}/elasticsearch.yml"

# ctx logger info "Deploying Elasticsearch Logging Configuration file..."
# tmp_es_logging_conf_path=$(ctx download-resource "components/elasticsearch/config/logging.yml")
# sudo mv ${tmp_es_logging_conf_path} "${ELASTICSEARCH_CONF_PATH}/logging.yml"

ctx logger info "Configuring logrotate..."
lconf="/etc/logrotate.d/elasticsearch"
cat << EOF | sudo tee $lconf > /dev/null
$ELASTICSEARCH_LOG_PATH/*.log {
    daily
    rotate 7
    size 100M
    copytruncate
    compress
    delaycompress
    missingok
    notifempty
    create 644 elasticsearch elasticsearch
}
EOF
sudo chmod 644 $lconf


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

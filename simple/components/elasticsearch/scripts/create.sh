#!/bin/bash -e

. $(ctx download-resource "components/utils")
. $(ctx download-resource "components/elasticsearch/scripts/configure_es")


CONFIG_REL_PATH="components/elasticsearch/config"

export ES_JAVA_OPRT=$(ctx node properties es_java_opts)  # (e.g. "-Xmx1024m -Xms1024m")
export ELASTICHSEARCH_SOURCE_URL=$(ctx node properties es_rpm_source_url)  # (e.g. "https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.3.tar.gz")
export ELASTICSEARCH_INDEX_ROTATION_DAY_COUNT=$(ctx node properties es_index_rotation_day_count)

export ELASTICSEARCH_PORT="9200"
export ELASTICSEARCH_HOME="/opt/elasticsearch"
export ELASTICSEARCH_LOG_PATH="/var/log/cloudify/elasticsearch"
export ELASTICSEARCH_CONF_PATH="/etc/elasticsearch"


ctx logger info "Installing Elasticsearch..."

copy_notice "elasticsearch"
create_dir ${ELASTICSEARCH_HOME}
create_dir ${ELASTICSEARCH_LOG_PATH}

yum_install ${ELASTICHSEARCH_SOURCE_URL}

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

ctx logger info "Installing Elasticsearch Curator..."
install_module "elasticsearch-curator==3.2.0"

rotator_script=$(ctx download-resource components/elasticsearch/scripts/rotate_es_indices)
replace "{{ ctx.node.properties.elasticsearch_index_rotation_day_count }}" "${ELASTICSEARCH_INDEX_ROTATION_DAY_COUNT}" $rotator_script

ctx logger info "Configuring Elasticsearch Index Rotation cronjob for logstash-YYYY.mm.dd index patterns..."
# testable manually by running: sudo run-parts /etc/cron.daily
sudo mv ${rotator_script} /etc/cron.daily/rotate_es_indices
sudo chown -R root:root /etc/cron.daily/rotate_es_indices
sudo chmod +x /etc/cron.daily/rotate_es_indices
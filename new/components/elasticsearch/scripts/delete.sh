#!/bin/bash -e

. $(ctx download-resource "components/utils")


export ELASTICHSEARCH_SOURCE_URL=$(ctx node properties es_tar_source_url)  # (e.g. "https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.3.tar.gz")

export ELASTICSEARCH_HOME="/opt/elasticsearch"
export ELASTICSEARCH_LOG_PATH="/var/log/cloudify/elasticsearch"


ctx logger info "Uninstalling Elasticsearch..."

# needed?
# ctx logger info "Removing Elasticsearch Service..."
# sudo systemctl disable elasticsearch.service

remove_notice "elasticsearch"
remove_dir ${ELASTICSEARCH_HOME}
remove_dir ${ELASTICSEARCH_LOG_PATH}

yum_uninstall ${ELASTICHSEARCH_SOURCE_URL}

#!/bin/bash -e

# export ELASTICSEARCH_HOME="/opt/elasticsearch"

ctx logger info "Starting Elasticsearch..."
# nohup sudo -E ${ELASTICSEARCH_HOME}/bin/elasticsearch -d >& /dev/null < /dev/null &
sudo systemctl start elasticsearch.service
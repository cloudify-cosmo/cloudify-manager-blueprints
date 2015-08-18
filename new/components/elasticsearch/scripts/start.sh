#!/bin/bash -e

export ELASTICSEARCH_HOME="/opt/elasticsearch"

ctx logger info "Starting Elasticsearch..."
sudo systemctl start elasticsearch.service
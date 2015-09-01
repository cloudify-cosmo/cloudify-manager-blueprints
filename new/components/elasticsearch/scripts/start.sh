#!/bin/bash -e

export ELASTICSEARCH_HOME="/opt/elasticsearch"

ctx logger info "Starting Elasticsearch Service..."
sudo systemctl start elasticsearch.service
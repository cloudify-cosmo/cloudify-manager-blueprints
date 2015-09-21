#!/bin/bash -e

export ELASTICSEARCH_HOME="/opt/elasticsearch"

ctx logger info "Stopping Elasticsearch Service..."
sudo systemctl stop elasticsearch.service

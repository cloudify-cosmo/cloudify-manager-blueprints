#!/bin/bash -e

ES_ENDPOINT_IP=$(ctx node properties es_endpoint_ip)

if [ -z "${ES_ENDPOINT_IP}"]; then
    ctx logger info "Starting Elasticsearch..."
    sudo systemctl start elasticsearch.service
fi

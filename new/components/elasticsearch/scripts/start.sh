#!/bin/bash -e

ES_ENDPOINT_IP=$(ctx node properties es_endpoint_ip)

if [ "${ES_ENDPOINT_IP}" == "localhost" ]; then
    ctx logger info "Starting Elasticsearch..."
    sudo systemctl start elasticsearch.service
fi

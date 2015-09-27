#!/bin/bash -e

INFLUXDB_ENDPOINT_IP=$(ctx node properties influxdb_endpoint_ip)

if [ "${INFLUXDB_ENDPOINT_IP}" == "localhost" ]; then
    ctx logger info "Starting InfluxDB Service..."
    sudo systemctl start cloudify-influxdb.service
fi

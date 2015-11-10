#!/bin/bash -e

ctx logger info "Starting AMQP InfluxDB Broker Service..."
sudo systemctl start cloudify-amqpinflux.service
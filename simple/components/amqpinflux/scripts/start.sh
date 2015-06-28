#!/bin/bash -e

ctx logger info "AMQP InfluxDB Broker..."
sudo systemctl start cloudify-amqpinflux.service
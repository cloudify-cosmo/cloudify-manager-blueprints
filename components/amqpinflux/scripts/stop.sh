#!/bin/bash -e

ctx logger info "Stopping AMQP InfluxDB Broker Service..."
sudo systemctl stop cloudify-amqpinflux.service
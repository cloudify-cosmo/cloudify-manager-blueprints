#!/bin/bash -e

ctx logger info "Starting InfluxDB Service..."
sudo systemctl start cloudify-influxdb.service
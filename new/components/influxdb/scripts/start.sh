#!/bin/bash -e

ctx logger info "Starting InfluxDB..."
sudo systemctl start cloudify-influxdb.service
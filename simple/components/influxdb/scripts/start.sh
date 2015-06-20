#!/bin/bash -e

# export INFLUXDB_HOME="/opt/influxdb"

ctx logger info "Starting InfluxDB..."
sudo /etc/init.d/influxdb start
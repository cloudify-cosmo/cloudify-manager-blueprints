#!/bin/bash -e

ctx logger info "Stopping InfluxDB Service..."
sudo systemctl stop cloudify-influxdb.service

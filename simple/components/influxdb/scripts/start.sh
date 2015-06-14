#!/bin/bash -e

export INFLUXDB_HOME="/opt/influxdb"

ctx logger info "Executing: sudo -E /usr/bin/influxdb -config=${INFLUXDB_HOME}/shared/config.toml &..."
sudo -E /usr/bin/influxdb-daemon -config=${INFLUXDB_HOME}/shared/config.toml > /dev/null 2>&1 &
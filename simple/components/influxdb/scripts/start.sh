#!/bin/bash -e

# export INFLUXDB_HOME="/opt/influxdb"

ctx logger info "Starting InfluxDB..."
# note that the influxdb-daemon runs with nohup. Moving to systemd or else we shouldn't use the daemon.
# sudo -E /usr/bin/influxdb-daemon -config=${INFLUXDB_HOME}/shared/config.toml >& /dev/null < /dev/null &
sudo /etc/init.d/influxdb start
#!/bin/bash -e

. $(ctx download-resource "components/utils")


export INFLUXDB_PORT=$(ctx node properties influxdb_api_port)  # (e.g. "8086")
export INFLUXDB_SOURCE_URL=$(ctx node properties influxdb_rpm_source_url)  # (e.g. "https://s3.amazonaws.com/influxdb/influxdb-0.8.8-1.x86_64.rpm")

export INFLUXDB_HOME="/opt/influxdb"
export INFLUXDB_LOG_PATH="/var/log/cloudify/influxdb"



ctx logger info "Uninstalling InfluxDB..."

remove_systemd_service "influxdb"

remove_notice "influxdb"
# might be removed by uninstall process - test
# remove_dir ${INFLUXDB_HOME}
remove_dir ${INFLUXDB_LOG_PATH}

yum_uninstall ${INFLUXDB_SOURCE_URL}

ctx logger info "Removing Relevant Files..."
sudo rm "/etc/logrotate.d/influxdb"
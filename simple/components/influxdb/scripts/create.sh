#!/bin/bash

INFLUXDB_VERSION="0.8.8"
INFLUXDB_HOME="/opt/influxdb"
INFLUXDB_LOG_PATH="/var/log/cloudify/influxdb"
# INFLUXDB_PORT=$(ctx node properties influxdb_port)
INFLUXDB_PORT="8086"
# INFLUXDB_SOURCE_URL=$(ctx node properties influxdb_rpm_source_url)
INFLUXDB_SOURCE_URL="http://get.influxdb.org/influxdb-${INFLUXDB_VERSION}-1.x86_64.rpm"


function import_helpers
{
    if [ ! -e "/tmp/utils" ]; then
        cp components/utils /tmp/utils
        # ctx download-resource "components/utils" '@{"target_path": "/tmp/utils"}'
    fi
    . /tmp/utils
    # required only in current vagrant environment otherwise passed to the vm via the script plugin
    . components/env_vars
}

function main
{

    log_section "Installing InfluxDB..."

    copy_notice "influxdb" && \
    create_dir ${INFLUXDB_HOME} && \
    create_dir ${INFLUXDB_HOME}/scripts && \
    create_dir ${INFLUXDB_LOG_PATH} && \

    install_rpm ${INFLUXDB_SOURCE_URL} && \

    log DEBUT "Deploying InfluxDB Config file..."
    # ctx download-resource components/influxdb/config/config.toml '@{"target_path": "/tmp/config.toml"}'
    sudo cp "components/influxdb/config/config.toml" "/tmp/config.toml" && \
    sudo mv "/tmp/config.toml" "${INFLUXDB_HOME}/shared/config.toml" && \

    log DEBUG "Starting InfluxDB for configuration purposes..."
    sudo /usr/bin/influxdb-daemon -config=${INFLUXDB_HOME}/shared/config.toml && \
    log DEBUG "Waiting for InfluxDB to become available..."
    wait_for_port "${INFLUXDB_PORT}"
    log DEBUG "Creating InfluxDB Database..."
    sudo curl "http://localhost:8086/db?u=root&p=root" -d "{\"name\": \"cloudify\"}" && \
    curl 'http://localhost:8086/cluster_admins?u=root&p=root'
    log DEBUG "Killing InfluxDB..."
    sudo pkill -f influxdb
}

cd /vagrant
import_helpers
main
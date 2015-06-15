#!/bin/bash -e

export INFLUXDB_HOME="/opt/influxdb"
export INFLUXDB_LOG_PATH="/var/log/cloudify/influxdb"
export INFLUXDB_PORT=$(ctx node properties influxdb_port)  # (e.g. "8086")
export INFLUXDB_SOURCE_URL=$(ctx node properties influxdb_rpm_source_url)  # (e.g. "http://get.influxdb.org/influxdb-0.8.8-1.x86_64.rpm")


function import_helpers
{
    if [ ! -e "/tmp/utils" ]; then
        cp components/utils /tmp/utils
        # ctx download-resource "components/utils" '@{"target_path": "/tmp/utils"}'
    fi
    . /tmp/utils
}

function main
{

    ctx logger info "Installing InfluxDB..."

    copy_notice "influxdb" && \
    create_dir ${INFLUXDB_HOME} && \
    create_dir ${INFLUXDB_HOME}/scripts && \
    create_dir ${INFLUXDB_LOG_PATH} && \

    install_rpm ${INFLUXDB_SOURCE_URL} && \

    ctx logger info "Deploying InfluxDB Config file..."
    # ctx download-resource components/influxdb/config/config.toml '@{"target_path": "/tmp/config.toml"}'
    sudo cp "components/influxdb/config/config.toml" "/tmp/config.toml" && \
    sudo mv "/tmp/config.toml" "${INFLUXDB_HOME}/shared/config.toml" && \

    ctx logger info "Starting InfluxDB for configuration purposes..."
    sudo -E /usr/bin/influxdb-daemon -config=${INFLUXDB_HOME}/shared/config.toml && \
    ctx logger info "Waiting for InfluxDB to become available..."
    wait_for_port "${INFLUXDB_PORT}"
    ctx logger info "Creating InfluxDB Database..."
    sudo curl "http://localhost:8086/db?u=root&p=root" -d "{\"name\": \"cloudify\"}" && \
    test_db_creation=$(curl 'http://localhost:8086/cluster_admins?u=root&p=root') && \
    ctx logger info "InfluxDB Database Creation test: ${test_db_creation}"
    ctx logger info "Killing InfluxDB..."
    sudo pkill -f influxdb
}

cd /vagrant
import_helpers
main
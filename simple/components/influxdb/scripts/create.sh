#!/bin/bash -e

. $(ctx download-resource "components/utils")


export INFLUXDB_PORT=$(ctx node properties influxdb_api_port)  # (e.g. "8086")
export INFLUXDB_SOURCE_URL=$(ctx node properties influxdb_rpm_source_url)  # (e.g. "https://s3.amazonaws.com/influxdb/influxdb-0.8.8-1.x86_64.rpm")

export INFLUXDB_HOME="/opt/influxdb"
export INFLUXDB_LOG_PATH="/var/log/cloudify/influxdb"



ctx logger info "Installing InfluxDB..."

copy_notice "influxdb"
create_dir ${INFLUXDB_HOME}
create_dir ${INFLUXDB_HOME}/scripts
create_dir ${INFLUXDB_LOG_PATH}

yum_install ${INFLUXDB_SOURCE_URL}

# influxdb 0.8 rotates its log files every midnight
# so that's the files we going to logrotate here (*.txt.*)
lconf="/etc/logrotate.d/influxdb"
config="$INFLUXDB_LOG_PATH/*.txt.* {
        daily
        rotate 7
        compress
        delaycompress
        missingok
        notifempty
}"

ctx logger info "Configuring logrotate..."
echo "$config" | sudo tee $lconf
sudo chmod 644 $lconf

ctx logger info "Deploying InfluxDB Config file..."
influx_config=$(ctx download-resource "components/influxdb/config/config.toml")
sudo mv ${influx_config} "${INFLUXDB_HOME}/shared/config.toml"

ctx logger info "Chowning InfluxDB logs path..."
sudo chown -R influxdb:influxdb ${INFLUXDB_LOG_PATH}

configure_systemd_service "influxdb"

ctx logger info "Starting InfluxDB for configuration purposes..."
sudo systemctl start cloudify-influxdb.service
ctx logger info "Waiting for InfluxDB to become available..."
wait_for_port "${INFLUXDB_PORT}"
ctx logger info "Creating InfluxDB Database..."
sudo curl "http://localhost:8086/db?u=root&p=root" -d "{\"name\": \"cloudify\"}"
test_db_creation=$(curl 'http://localhost:8086/cluster_admins?u=root&p=root')
ctx logger info "InfluxDB Database Creation test: ${test_db_creation}"
ctx logger info "Killing InfluxDB..."
sudo systemctl stop cloudify-influxdb.service
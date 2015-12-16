#!/bin/bash -e

. $(ctx download-resource "components/utils")
. $(ctx download-resource "components/influxdb/scripts/configure_influx")


CONFIG_REL_PATH="components/influxdb/config"

export INFLUXDB_SOURCE_URL=$(ctx node properties influxdb_rpm_source_url)
export INFLUXDB_ENDPOINT_IP=$(ctx node properties influxdb_endpoint_ip)
# currently, cannot be changed due to the webui not allowing to configure it.
export INFLUXDB_ENDPOINT_PORT="8086"

export INFLUXDB_USER="influxdb"
export INFLUXDB_GROUP="influxdb"
export INFLUXDB_HOME="/opt/influxdb"
export INFLUXDB_LOG_PATH="/var/log/cloudify/influxdb"


function install_influxdb() {
    ctx logger info "Installing InfluxDB..."
    set_selinux_permissive

    copy_notice "influxdb"
    create_dir ${INFLUXDB_HOME}
    create_dir ${INFLUXDB_LOG_PATH}

    yum_install ${INFLUXDB_SOURCE_URL}
    sudo rm -f /etc/init.d/influxdb
    
    # influxdb 0.8 rotates its log files every midnight
    # so that's the files we going to logrotate here (*.txt.*)
    deploy_logrotate_config "influxdb"

    ctx logger info "Deploying InfluxDB Config file..."
    deploy_blueprint_resource "${CONFIG_REL_PATH}/config.toml" "${INFLUXDB_HOME}/shared/config.toml"

    ctx logger info "Fixing permissions..."
    sudo chown -R "${INFLUXDB_USER}:${INFLUXDB_GROUP}" "${INFLUXDB_HOME}"
    sudo chown -R "${INFLUXDB_USER}:${INFLUXDB_GROUP}" "${INFLUXDB_LOG_PATH}"

    ctx logger info "Chowning InfluxDB logs path..."
    sudo chown -R influxdb:influxdb ${INFLUXDB_LOG_PATH}

    configure_systemd_service "influxdb"
}

if [ -z "${INFLUXDB_ENDPOINT_IP}" ]; then
    INFLUXDB_ENDPOINT_IP=$(ctx instance host_ip)
    install_influxdb

    ctx logger info "Starting InfluxDB Service..."
    sudo systemctl start cloudify-influxdb.service

    wait_for_port "${INFLUXDB_ENDPOINT_PORT}" "${INFLUXDB_ENDPOINT_IP}"
    # per a function in configure_influx
    configure_influxdb "${INFLUXDB_ENDPOINT_IP}" "${INFLUXDB_ENDPOINT_PORT}"

    ctx logger info "Stopping InfluxDB Service..."
    sudo systemctl stop cloudify-influxdb.service
else
    ctx logger info "External InfluxDB Endpoint IP provided: ${INFLUXDB_ENDPOINT_IP}..."
    sleep 5
    wait_for_port "${INFLUXDB_ENDPOINT_PORT}" "${INFLUXDB_ENDPOINT_IP}"
    # per a function in configure_influx
    configure_influxdb "${INFLUXDB_ENDPOINT_IP}" "${INFLUXDB_ENDPOINT_PORT}"
fi

ctx instance runtime_properties influxdb_endpoint_ip ${INFLUXDB_ENDPOINT_IP}

#!/bin/bash -e

. $(ctx download-resource "components/utils")


export AMQPINFLUX_HOME="/opt/amqpinflux"
export AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"
export AMQPINFLUX_SOURCE_URL=$(ctx node properties amqpinflux_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-amqp-influxdb/archive/3.2.zip")

ctx logger info "Uninstalling AQMPInflux..."

remove_systemd_service "amqpinflux"
remove_notice "amqpinflux"
remove_dir "${AMQPINFLUX_HOME}"
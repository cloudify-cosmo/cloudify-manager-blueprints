#!/bin/bash -e

. $(ctx download-resource "components/utils")


export AMQPINFLUX_HOME="/opt/amqpinflux"
export AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"
export AMQPINFLUX_SOURCE_URL=$(ctx node properties amqpinflux_module_source_url)

ctx logger info "Installing AQMPInflux..."

copy_notice "amqpinflux"
create_dir "${AMQPINFLUX_HOME}"
create_virtualenv "${AMQPINFLUX_VIRTUALENV_DIR}"
install_module ${AMQPINFLUX_SOURCE_URL} "${AMQPINFLUX_VIRTUALENV_DIR}"
configure_systemd_service "amqpinflux"
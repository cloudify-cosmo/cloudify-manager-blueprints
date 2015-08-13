#!/bin/bash -e

. $(ctx download-resource "components/utils")


export AMQPINFLUX_HOME="/opt/amqpinflux"
export AMQPINFLUX_USER="amqpinflux"
export AMQPINFLUX_GROUP="amqpinflux"
export AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"
export AMQPINFLUX_SOURCE_URL=$(ctx node properties amqpinflux_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-amqp-influxdb/archive/3.2.zip")

ctx logger info "Installing AQMPInflux..."

copy_notice "amqpinflux"

create_dir "${AMQPINFLUX_HOME}"
create_virtualenv "${AMQPINFLUX_VIRTUALENV_DIR}"
install_module ${AMQPINFLUX_SOURCE_URL} "${AMQPINFLUX_VIRTUALENV_DIR}"

ctx logger info "Creating user..."
sudo useradd --shell /sbin/nologin --home-dir "${AMQPINFLUX_HOME}" --no-create-home --system "${AMQPINFLUX_USER}"

ctx logger info "Fixing permissions..."
sudo chown -R "${AMQPINFLUX_USER}:${AMQPINFLUX_GROUP}" "${AMQPINFLUX_HOME}"
configure_systemd_service "amqpinflux"
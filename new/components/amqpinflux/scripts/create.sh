#!/bin/bash -e

. $(ctx download-resource "components/utils")

export AMQPINFLUX_RPM_SOURCE_URL=$(ctx node properties amqpinflux_rpm_source_url)
export AMQPINFLUX_SOURCE_URL=$(ctx node properties amqpinflux_module_source_url)

export AMQPINFLUX_HOME="/opt/amqpinflux"
export AMQPINFLUX_USER="amqpinflux"
export AMQPINFLUX_GROUP="amqpinflux"
export AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"

ctx logger info "Installing AQMPInflux..."
set_selinux_permissive

copy_notice "amqpinflux"
create_dir "${AMQPINFLUX_HOME}"

# this creates the AMQPINFLUX_VIRTUALENV_DIR and installs the module into it.
yum_install ${AMQPINFLUX_RPM_SOURCE_URL}
# this allows to upgrade amqpinflux if necessary.
[ -z "${AMQPINFLUX_SOURCE_URL}" ] || install_module ${AMQPINFLUX_SOURCE_URL} "${AMQPINFLUX_VIRTUALENV_DIR}"

ctx logger info "Creating user..."
sudo useradd --shell /sbin/nologin --home-dir "${AMQPINFLUX_HOME}" --no-create-home --system "${AMQPINFLUX_USER}"

ctx logger info "Fixing permissions..."
sudo chown -R "${AMQPINFLUX_USER}:${AMQPINFLUX_GROUP}" "${AMQPINFLUX_HOME}"

configure_systemd_service "amqpinflux"
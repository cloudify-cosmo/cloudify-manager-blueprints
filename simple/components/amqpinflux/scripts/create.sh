#!/bin/bash

AMQPINFLUX_VERSION="3.2"
AMQP_HOST="localhost"
INFLUXDB_HOST="localhost"
AMQPINFLUX_HOME="/opt/amqpinflux"
AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"
# AMQPINFLUX_SOURCE_URL=$(ctx node properties amqpinflux_source_url)
AMQPINFLUX_SOURCE_URL="https://github.com/cloudify-cosmo/cloudify-amqp-influxdb/archive/${AMQPINFLUX_VERSION}.zip"


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
    log_section "Installing AQMPInflux..."

    copy_notice "amqpinflux" && \
    create_dir "${AMQPINFLUX_HOME}" && \
    create_virtualenv "${AMQPINFLUX_VIRTUALENV_DIR}" && \
    install_module ${AMQPINFLUX_SOURCE_URL} "${AMQPINFLUX_VIRTUALENV_DIR}"
}

cd /vagrant
import_helpers
main
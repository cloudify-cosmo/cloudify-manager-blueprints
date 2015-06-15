#!/bin/bash -e

export AMQPINFLUX_HOME="/opt/amqpinflux"
export AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"
export AMQPINFLUX_SOURCE_URL=$(ctx node properties amqpinflux_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-amqp-influxdb/archive/3.2.zip")


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
    ctx logger info "Installing AQMPInflux..."

    copy_notice "amqpinflux" && \
    create_dir "${AMQPINFLUX_HOME}" && \
    create_virtualenv "${AMQPINFLUX_VIRTUALENV_DIR}" && \
    install_module ${AMQPINFLUX_SOURCE_URL} "${AMQPINFLUX_VIRTUALENV_DIR}"
}

cd /vagrant
import_helpers
main
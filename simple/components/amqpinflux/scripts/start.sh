#!/bin/bash

AMQPINFLUX_HOME="/opt/amqpinflux"
AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"

function main
{
    sudo -E ${AMQPINFLUX_VIRTUALENV_DIR}/bin/python ${AMQPINFLUX_VIRTUALENV_DIR}/bin/cloudify-amqp-influxdb \
    --amqp-exchange cloudify-monitoring \
    --amqp-routing-key '*' \
    --amqp-hostname localhost \
    --influx-database cloudify \
    --influx-hostname localhost &
}

main

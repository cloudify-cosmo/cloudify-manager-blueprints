#!/bin/bash

AMQP_HOST="localhost"
INFLUXDB_HOST="localhost"
AMQPINFLUX_HOME="/opt/amqpinflux"
AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"

sudo -E ${AMQPINFLUX_VIRTUALENV_DIR}/bin/python ${AMQPINFLUX_VIRTUALENV_DIR}/bin/cloudify-amqp-influxdb \
--amqp-exchange cloudify-monitoring \
--amqp-routing-key '*' \
--amqp-hostname ${AMQP_HOST} \
--influx-database cloudify \
--influx-hostname ${INFLUXDB_HOST} &
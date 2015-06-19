#!/bin/bash -e

export AMQP_HOST="localhost"
export INFLUXDB_HOST="localhost"
export AMQPINFLUX_HOME="/opt/amqpinflux"
export AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"

ctx logger info "AMQP InfluxDB Broker..."
nohup sudo -E ${AMQPINFLUX_VIRTUALENV_DIR}/bin/python ${AMQPINFLUX_VIRTUALENV_DIR}/bin/cloudify-amqp-influxdb \
--amqp-exchange cloudify-monitoring \
--amqp-routing-key '*' \
--amqp-hostname ${AMQP_HOST} \
--influx-database cloudify \
--influx-hostname ${INFLUXDB_HOST} >& /dev/null < /dev/null &
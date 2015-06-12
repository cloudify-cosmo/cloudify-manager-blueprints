FROM cloudify_pythonbase
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY AMQPINFLUX_NOTICE.txt /root/AMQPINFLUX_NOTICE.txt

ENV AMQP_INFLUX_VERSION=master \
    DOCKER_ENV=True \
    AMQP_HOST=rabbitmq \
    INFLUXDB_HOST=influxdb \
    AMQPINFLUX_HOME=/opt/amqpinflux
ENV VIRTUALENV_DIR=${AMQPINFLUX_HOME}/env

RUN mkdir -p ${AMQPINFLUX_HOME} && \
    virtualenv ${VIRTUALENV_DIR} && \
    ${VIRTUALENV_DIR}/bin/pip install https://github.com/cloudify-cosmo/cloudify-amqp-influxdb/archive/${AMQP_INFLUX_VERSION}.zip

CMD ${VIRTUALENV_DIR}/bin/python ${VIRTUALENV_DIR}/bin/cloudify-amqp-influxdb \
    --amqp-exchange cloudify-monitoring \
    --amqp-routing-key '*' \
    --amqp-hostname rabbitmq \
    --influx-database cloudify \
    --influx-hostname influxdb
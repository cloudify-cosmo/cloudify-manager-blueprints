FROM debian:jessie
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY RABBITMQ_NOTICE.txt /root/RABBITMQ_NOTICE.txt

ENV DOCKER_ENV=True \
    RABBITMQ_LOG_BASE=/var/log/cloudify/rabbitmq

RUN apt-get update && \
    apt-get install -y logrotate erlang-nox && \
    apt-get -y install rabbitmq-server && \
    rabbitmq-plugins enable rabbitmq_management && \
    rabbitmq-plugins enable rabbitmq_tracing && \
    # enable guest user access where cluster not on localhost
    echo "[{rabbit, [{loopback_users, []}]}]." > /etc/rabbitmq/rabbitmq.config && \
    mkdir -p /var/log/cloudify/rabbitmq && \
    chown rabbitmq:rabbitmq /var/log/cloudify/rabbitmq && \
    rm -rf /var/lib/apt/lists && \
    apt-get autoremove -y

EXPOSE 5672 15672 4369

CMD rabbitmq-server

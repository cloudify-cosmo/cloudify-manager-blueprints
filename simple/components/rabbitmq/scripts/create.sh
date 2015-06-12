#!/bin/bash

RABBITMQ_VERSION="3.5.3"
ERLANG_VERSION="17.4"
RABBITMQ_LOG_BASE="/var/log/cloudify/rabbitmq"
# ERLANG_SOURCE_URL=$(ctx node properties erlang_rpm_source_url)
ERLANG_SOURCE_URL="http://www.rabbitmq.com/releases/erlang/erlang-${ERLANG_VERSION}-1.el6.x86_64.rpm"
# RABBITMQ_SOURCE_URL=$(ctx node properties rabbitmq_rpm_source_url)
RABBITMQ_SOURCE_URL="http://www.rabbitmq.com/releases/rabbitmq-server/v${RABBITMQ_VERSION}/rabbitmq-server-${RABBITMQ_VERSION}-1.noarch.rpm"


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
    log_section "Installing RabbitMQ..."

    copy_notice "rabbitmq" && \
    create_dir "${RABBITMQ_LOG_BASE}" && \

    log DEBUG "Installing logrotate"
    sudo yum install logrotate -y && \
    install_rpm ${ERLANG_SOURCE_URL} && \
    install_rpm ${RABBITMQ_SOURCE_URL} && \

    # Dunno if required.. the key thing, that is...
    # curl --fail --location http://www.rabbitmq.com/releases/rabbitmq-server/v${RABBITMQ_VERSION}/rabbitmq-server-${RABBITMQ_VERSION}-1.noarch.rpm -o /tmp/rabbitmq.rpm
    # sudo rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
    # sudo yum install /tmp/rabbitmq.rpm -y

    log DEBUG "Starting RabbitMQ Server in Daemonized mode..."
    sudo rabbitmq-server -detached && \

    log DEBUG "Enabling RabbitMQ Plugins..."
    sudo rabbitmq-plugins enable rabbitmq_management && \
    sudo rabbitmq-plugins enable rabbitmq_tracing && \

    # enable guest user access where cluster not on localhost
    log DEBUG "Enabling RabbitMQ user access..."
    echo "[{rabbit, [{loopback_users, []}]}]." | sudo tee --append /etc/rabbitmq/rabbitmq.config && \

    log DEBUG "Chowning RabbitMQ Log Path..."
    sudo chown rabbitmq:rabbitmq ${RABBITMQ_LOG_BASE} && \

    log DEBUG "Killing RabbitMQ..."
    sudo pkill -f rabbitmq
}

cd /vagrant
import_helpers
main
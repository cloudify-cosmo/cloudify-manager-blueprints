#!/bin/bash -e

export RABBITMQ_VERSION="3.5.3"
export ERLANG_VERSION="17.4"
export RABBITMQ_LOG_BASE="/var/log/cloudify/rabbitmq"
export ERLANG_SOURCE_URL=$(ctx node properties erlang_rpm_source_url)
# export ERLANG_SOURCE_URL="http://www.rabbitmq.com/releases/erlang/erlang-${ERLANG_VERSION}-1.el6.x86_64.rpm"
export RABBITMQ_SOURCE_URL=$(ctx node properties rabbitmq_rpm_source_url)
# export RABBITMQ_SOURCE_URL="http://www.rabbitmq.com/releases/rabbitmq-server/v${RABBITMQ_VERSION}/rabbitmq-server-${RABBITMQ_VERSION}-1.noarch.rpm"


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
    ctx logger info "Installing RabbitMQ..."

    copy_notice "rabbitmq" && \
    create_dir "${RABBITMQ_LOG_BASE}" && \

    ctx logger info "Installing logrotate"
    sudo yum install logrotate -y && \
    install_rpm ${ERLANG_SOURCE_URL} && \
    install_rpm ${RABBITMQ_SOURCE_URL} && \

    # Dunno if required.. the key thing, that is...
    # curl --fail --location http://www.rabbitmq.com/releases/rabbitmq-server/v${RABBITMQ_VERSION}/rabbitmq-server-${RABBITMQ_VERSION}-1.noarch.rpm -o /tmp/rabbitmq.rpm
    # sudo rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
    # sudo yum install /tmp/rabbitmq.rpm -y

    ctx logger info "Starting RabbitMQ Server in Daemonized mode..."
    sudo rabbitmq-server -detached && \

    ctx logger info "Enabling RabbitMQ Plugins..."
    sudo rabbitmq-plugins enable rabbitmq_management && \
    sudo rabbitmq-plugins enable rabbitmq_tracing && \

    # enable guest user access where cluster not on localhost
    ctx logger info "Enabling RabbitMQ user access..."
    echo "[{rabbit, [{loopback_users, []}]}]." | sudo tee --append /etc/rabbitmq/rabbitmq.config && \

    ctx logger info "Chowning RabbitMQ Log Path..."
    sudo chown rabbitmq:rabbitmq ${RABBITMQ_LOG_BASE} && \

    ctx logger info "Killing RabbitMQ..."
    sudo pkill -f rabbitmq
}

cd /vagrant
import_helpers
main
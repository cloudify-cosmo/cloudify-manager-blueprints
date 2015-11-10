#!/bin/bash -e

export RABBITMQ_ENDPOINT_IP=$(ctx node properties rabbitmq_endpoint_ip)

if [[ -z "${RABBITMQ_ENDPOINT_IP}" ]]; then
    ctx logger info "Starting RabbitMQ Service..."
    sudo systemctl start cloudify-rabbitmq.service


    # This should be done in the create.sh script. For some reason, it fails. Need to check.
    export RABBITMQ_EVENTS_QUEUE_MESSAGE_TTL=$(ctx node properties rabbitmq_events_queue_message_ttl)
    export RABBITMQ_LOGS_QUEUE_MESSAGE_TTL=$(ctx node properties rabbitmq_logs_queue_message_ttl)
    export RABBITMQ_METRICS_QUEUE_MESSAGE_TTL=$(ctx node properties rabbitmq_metrics_queue_message_ttl)
    export RABBITMQ_EVENTS_QUEUE_LENGTH_LIMIT=$(ctx node properties rabbitmq_events_queue_length_limit)
    export RABBITMQ_LOGS_QUEUE_LENGTH_LIMIT=$(ctx node properties rabbitmq_logs_queue_length_limit)
    export RABBITMQ_METRICS_QUEUE_LENGTH_LIMIT=$(ctx node properties rabbitmq_metrics_queue_length_limit)


    sleep 30

    ctx logger info "Setting RabbitMQ Policies..."
    ctx logger info "Setting cloudify-logs queue message-ttl to ${RABBITMQ_LOGS_QUEUE_MESSAGE_TTL}..."
    sudo rabbitmqctl set_policy logs_queue_message_ttl "^cloudify-logs$" "{"\"message-ttl"\":${RABBITMQ_LOGS_QUEUE_MESSAGE_TTL}}" --apply-to queues >/dev/null
    ctx logger info "Setting cloudify-events queue message-ttl to ${RABBITMQ_EVENTS_QUEUE_MESSAGE_TTL}..."
    sudo rabbitmqctl set_policy events_queue_message_ttl "^cloudify-events$" "{"\"message-ttl"\":${RABBITMQ_EVENTS_QUEUE_MESSAGE_TTL}}" --apply-to queues >/dev/null
    ctx logger info "Setting cloudify-monitoring queues message ttl to ${RABBITMQ_METRICS_QUEUE_MESSAGE_TTL}..."
    sudo rabbitmqctl set_policy metrics_queue_message_ttl "^amq\.gen.*$" "{"\"message-ttl"\":${RABBITMQ_METRICS_QUEUE_MESSAGE_TTL}}" --apply-to queues >/dev/null
    sudo rabbitmqctl set_policy riemann_deployment_queues_message_ttl "^.*-riemann$" "{"\"message-ttl"\":${RABBITMQ_METRICS_QUEUE_MESSAGE_TTL}}" --apply-to queues >/dev/null

    ctx logger info "Setting cloudify-logs queue length to ${RABBITMQ_LOGS_QUEUE_LENGTH_LIMIT}..."
    sudo rabbitmqctl set_policy logs_queue_length "^cloudify-logs$" "{"\"max-length"\":${RABBITMQ_LOGS_QUEUE_LENGTH_LIMIT}}" --apply-to queues >/dev/null
    ctx logger info "Setting cloudify-events queue length to ${RABBITMQ_EVENTS_QUEUE_LENGTH_LIMIT}..."
    sudo rabbitmqctl set_policy events_queue_length "^cloudify-events$" "{"\"max-length"\":${RABBITMQ_EVENTS_QUEUE_LENGTH_LIMIT}}" --apply-to queues >/dev/null
    ctx logger info "Setting cloudify-monitoring queues length to ${RABBITMQ_METRICS_QUEUE_LENGTH_LIMIT}..."
    sudo rabbitmqctl set_policy metrics_queue "^amq\.gen.*$" "{"\"max-length"\":${RABBITMQ_METRICS_QUEUE_LENGTH_LIMIT}}" --apply-to queues >/dev/null
    sudo rabbitmqctl set_policy riemann_deployment_queues "^.*-riemann$" "{"\"max-length"\":${RABBITMQ_METRICS_QUEUE_LENGTH_LIMIT}}" --apply-to queues >/dev/null
fi

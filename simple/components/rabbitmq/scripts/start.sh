#!/bin/bash -e

ctx logger info "Starting RabbitMQ Service..."
sudo systemctl start cloudify-rabbitmq.service


export RABBITMQ_EVENTS_QUEUE_LENGTH_LIMIT=$(ctx node properties rabbitmq_events_queue_length_limit)
export RABBITMQ_LOGS_QUEUE_LENGTH_LIMIT=$(ctx node properties rabbitmq_logs_queue_length_limit)
export RABBITMQ_METRICS_QUEUE_LENGTH_LIMIT=$(ctx node properties rabbitmq_metrics_queue_length_limit)

sleep 30

ctx logger info "Configuring RabbitMQ Policies..."
ctx logger info "Configuring cloudify-logs queue length to ${RABBITMQ_LOGS_QUEUE_LENGTH_LIMIT}..."
sudo rabbitmqctl set_policy logs_queue_length "^cloudify-logs$" "{"\"max-length"\":${RABBITMQ_LOGS_QUEUE_LENGTH_LIMIT}}" --apply-to queues >/dev/null
ctx logger info "Configuring cloudify-events queue length to ${RABBITMQ_EVENTS_QUEUE_LENGTH_LIMIT}..."
sudo rabbitmqctl set_policy events_queue_length "^cloudify-events$" "{"\"max-length"\":${RABBITMQ_EVENTS_QUEUE_LENGTH_LIMIT}}" --apply-to queues >/dev/null
ctx logger info "Configuring cloudify-monitoring queues length to ${RABBITMQ_METRICS_QUEUE_LENGTH_LIMIT}..."
sudo rabbitmqctl set_policy metrics_queue "^amq\.gen.*$" "{"\"max-length"\":${RABBITMQ_METRICS_QUEUE_LENGTH_LIMIT}}" --apply-to queues >/dev/null
sudo rabbitmqctl set_policy riemann_deployment_queues "^.*-riemann$" "{"\"max-length"\":${RABBITMQ_METRICS_QUEUE_LENGTH_LIMIT}}" --apply-to queues >/dev/null

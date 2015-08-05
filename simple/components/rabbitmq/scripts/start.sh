#!/bin/bash -e

ctx logger info "Starting RabbitMQ Service..."
sudo systemctl start cloudify-rabbitmq.service



export RABBITMQ_EVENTS_QUEUE_MESSAGE_TTL=$(ctx node properties rabbitmq_events_queue_message_ttl)
export RABBITMQ_LOGS_QUEUE_MESSAGE_TTL=$(ctx node properties rabbitmq_logs_queue_message_ttl)
export RABBITMQ_METRICS_QUEUE_MESSAGE_TTL=$(ctx node properties rabbitmq_metrics_queue_message_ttl)

sleep 30

ctx logger info "Configuring RabbitMQ Policies..."
ctx logger info "Configuring cloudify-logs queue message-ttl to ${RABBITMQ_LOGS_QUEUE_MESSAGE_TTL}..."
sudo rabbitmqctl set_policy logs_queue_message_ttl "^cloudify-logs$" "{"\"message-ttl"\":${RABBITMQ_LOGS_QUEUE_MESSAGE_TTL}}" --apply-to queues >/dev/null
ctx logger info "Configuring cloudify-events queue message-ttl to ${RABBITMQ_EVENTS_QUEUE_MESSAGE_TTL}..."
sudo rabbitmqctl set_policy events_queue_message_ttl "^cloudify-events$" "{"\"message-ttl"\":${RABBITMQ_EVENTS_QUEUE_MESSAGE_TTL}}" --apply-to queues >/dev/null
ctx logger info "Configuring cloudify-monitoring queues message ttl to ${RABBITMQ_METRICS_QUEUE_MESSAGE_TTL}..."
sudo rabbitmqctl set_policy metrics_queue_message_ttl "^amq\.gen.*$" "{"\"message-ttl"\":${RABBITMQ_METRICS_QUEUE_MESSAGE_TTL}}" --apply-to queues >/dev/null
sudo rabbitmqctl set_policy riemann_deployment_queues_message_ttl "^.*-riemann$" "{"\"message-ttl"\":${RABBITMQ_METRICS_QUEUE_MESSAGE_TTL}}" --apply-to queues >/dev/null

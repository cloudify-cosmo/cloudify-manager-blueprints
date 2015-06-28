#!/bin/bash -e

ctx logger info "Starting RabbitMQ Service..."
sudo systemctl start cloudify-rabbitmq.service
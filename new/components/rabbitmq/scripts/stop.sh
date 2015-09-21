#!/bin/bash -e

ctx logger info "Stopping RabbitMQ Service..."
sudo systemctl stop cloudify-rabbitmq.service
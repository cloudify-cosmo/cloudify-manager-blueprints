#!/usr/bin/env python

from time import sleep

from cloudify import ctx

import utils

rabbitmq_endpoint_ip = ctx.node.properties.get('rabbitmq_endpoint_ip')

if not rabbitmq_endpoint_ip:
    ctx.logger.info("Starting RabbitMQ Service...")
    utils.systemd.systemctl('start', 'cloudify-rabbitmq.service')
    # This should be done in the create.sh script.
    # For some reason, it fails. Need to check.

    rabbitmq_events_queue_message_ttl = ctx.node.properties[
        'rabbitmq_events_queue_message_ttl']
    rabbitmq_logs_queue_message_ttl = ctx.node.properties[
        'rabbitmq_logs_queue_message_ttl']
    rabbitmq_metrics_queue_message_ttl = ctx.node.properties[
        'rabbitmq_metrics_queue_message_ttl']
    rabbitmq_events_queue_length_limit = ctx.node.properties[
        'rabbitmq_events_queue_length_limit']
    rabbitmq_logs_queue_length_limit = ctx.node.properties[
        'rabbitmq_logs_queue_length_limit']
    rabbitmq_metrics_queue_length_limit = ctx.node.properties[
        'rabbitmq_metrics_queue_length_limit']

    # Sleep necessary to wait for service to be up to set these policies
    sleep(30)

    ctx.logger.info("Setting RabbitMQ Policies...")

    ctx.logger.info(
            "Setting cloudify-logs queue message-ttl to {0}...".format(
                    rabbitmq_logs_queue_message_ttl))
    utils.sudo(['rabbitmqctl', 'set_policy', 'logs_queue_message_ttl',
                '^cloudify-logs$',
                '{\"message-ttl\":'+str(rabbitmq_logs_queue_message_ttl)+"}",
                '--apply-to', 'queues'])

    ctx.logger.info(
            "Setting cloudify-events queue message-ttl to {0}...".format(
                    rabbitmq_events_queue_message_ttl))
    utils.sudo(['rabbitmqctl', 'set_policy', 'events_queue_message_ttl',
                '^cloudify-events$',
                '{\"message-ttl\":'+str(rabbitmq_events_queue_message_ttl)+"}",
                '--apply-to', 'queues'])

    ctx.logger.info(
            "Setting cloudify-monitoring queues message ttl to {0}...".format(
                    rabbitmq_metrics_queue_message_ttl))
    utils.sudo(['rabbitmqctl', 'set_policy', 'metrics_queue_message_ttl',
                '^amq\.gen.*$',
                '{\"message-ttl\":'+str(rabbitmq_metrics_queue_message_ttl)+"}",
                '--apply-to', 'queues'])
    utils.sudo(['rabbitmqctl', 'set_policy',
                'riemann_deployment_queues_message_ttl', '^.*-riemann$',
                '{\"message-ttl\":'+str(rabbitmq_metrics_queue_message_ttl)+"}",
                '--apply-to', 'queues'])

    ctx.logger.info(
            "Setting cloudify-logs queue length to {0}...".format(
                    rabbitmq_logs_queue_length_limit))
    utils.sudo(['rabbitmqctl', 'set_policy', 'logs_queue_length',
                '^cloudify-logs$',
                '{\"max-length\":'+str(rabbitmq_logs_queue_length_limit)+"}",
                '--apply-to', 'queues'])

    ctx.logger.info(
            "Setting cloudify-events queue length to {0}...".format(
                    rabbitmq_events_queue_length_limit))
    utils.sudo(['rabbitmqctl', 'set_policy', 'events_queue_length',
                '^cloudify-events$',
                '{\"max-length\":'+str(rabbitmq_events_queue_length_limit)+"}",
                '--apply-to', 'queues'])

    ctx.logger.info(
            "Setting cloudify-monitoring queues length to {0}...".format(
                    rabbitmq_metrics_queue_length_limit))
    utils.sudo(['rabbitmqctl', 'set_policy', 'metrics_queue',
                '^amq\.gen.*$',
                '{\"max-length\":'+str(rabbitmq_metrics_queue_length_limit)+"}",
                '--apply-to', 'queues'])
    utils.sudo(['rabbitmqctl', 'set_policy', 'riemann_deployment_queues',
                '^.*-riemann$',
                '{\"max-length\":'+str(rabbitmq_metrics_queue_length_limit)+"}",
                '--apply-to', 'queues'])

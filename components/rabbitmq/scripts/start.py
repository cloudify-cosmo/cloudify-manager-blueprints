#!/usr/bin/env python

import time
import json
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

RABBITMQ_SERVICE_NAME = 'rabbitmq'


ctx_properties = utils.ctx_factory.create(RABBITMQ_SERVICE_NAME,
                                          write_to_file=False)

rabbitmq_endpoint_ip = ctx_properties['rabbitmq_endpoint_ip']


def set_rabbitmq_policy(name, expression, policy):
    policy = json.dumps(policy)
    ctx.logger.info('Setting policy {0} on queues {1} to {2}'.format(
        name, expression, policy))
    # shlex screws this up because we need to pass json and shlex
    # strips quotes so we explicitly pass it as a list.
    utils.sudo(['rabbitmqctl', 'set_policy', name,
               expression, policy, '--apply-to', 'queues'])


if not rabbitmq_endpoint_ip:
    ctx.logger.info("Starting RabbitMQ Service...")
    utils.systemd.start(RABBITMQ_SERVICE_NAME)
    # This should be done in the create script.
    # For some reason, it fails. Need to check.

    events_queue_message_ttl = ctx_properties[
        'rabbitmq_events_queue_message_ttl']
    logs_queue_message_ttl = ctx_properties[
        'rabbitmq_logs_queue_message_ttl']
    metrics_queue_message_ttl = ctx_properties[
        'rabbitmq_metrics_queue_message_ttl']
    events_queue_length_limit = ctx_properties[
        'rabbitmq_events_queue_length_limit']
    logs_queue_length_limit = ctx_properties[
        'rabbitmq_logs_queue_length_limit']
    metrics_queue_length_limit = ctx_properties[
        'rabbitmq_metrics_queue_length_limit']

    utils.wait_for_port(5672)
    time.sleep(10)

    logs_queue_message_policy = {
        'message-ttl': logs_queue_message_ttl,
        'max-length': logs_queue_length_limit
    }
    events_queue_message_policy = {
        'message-ttl': events_queue_message_ttl,
        'max-length': events_queue_length_limit
    }
    metrics_queue_message_policy = {
        'message-ttl': metrics_queue_message_ttl,
        'max-length': metrics_queue_length_limit
    }
    riemann_deployment_queues_message_ttl = {
        'message-ttl': metrics_queue_message_ttl,
        'max-length': metrics_queue_length_limit
    }

    ctx.logger.info("Setting RabbitMQ Policies...")
    set_rabbitmq_policy(
        name='logs_queue_message_policy',
        expression='^cloudify-logs$',
        policy=logs_queue_message_policy
    )
    set_rabbitmq_policy(
        name='events_queue_message_policy',
        expression='^cloudify-events$',
        policy=events_queue_message_policy
    )
    set_rabbitmq_policy(
        name='metrics_queue_message_policy',
        expression='^amq\.gen.*$',
        policy=metrics_queue_message_policy
    )
    set_rabbitmq_policy(
        name='riemann_deployment_queues_message_ttl',
        expression='^.*-riemann$',
        policy=riemann_deployment_queues_message_ttl
    )

    # rabbitmq restart exits with 143 status code that is valid in this case.
    utils.start_service_and_archive_properties(RABBITMQ_SERVICE_NAME,
                                               ignore_restart_fail=True)

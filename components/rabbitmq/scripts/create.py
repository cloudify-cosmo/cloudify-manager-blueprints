#!/usr/bin/env python

import importlib
import os
from subprocess import check_output

utils_path = check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')


config_path = "components/rabbitmq/config"

rabbitmq_endpoint_ip = ctx.node.properties('rabbitmq_endpoint_ip')

# Sources
erlang_source_url = ctx.node.properties('erlang_rpm_source_url')
rabbitmq_source_url = ctx.node.properties('rabbitmq_rpm_source_url')

# General Configuration
rabbitmq_log_path = '/var/log/cloudify/rabbitmq'
rabbitmq_events_queue_message_ttl = ctx.node.properties(
    'rabbitmq_events_queue_message_ttl',
)
rabbitmq_logs_queue_message_ttl = ctx.node.properties(
    'rabbitmq_logs_queue_message_ttl',
)
rabbitmq_metrics_queue_message_ttl = ctx.node.properties(
    'rabbitmq_metrics_queue_message_ttl',
)
rabbitmq_events_queue_length_limit = ctx.node.properties(
    'rabbitmq_events_queue_length_limit',
)
rabbitmq_logs_queue_length_limit = ctx.node.properties(
    'rabbitmq_logs_queue_length_limit',
)
rabbitmq_metrics_queue_length_limit = ctx.node.properties(
    'rabbitmq_metrics_queue_length_limit',
)

# Security
rabbitmq_ssl_enabled = ctx.node.properties('rabbitmq_ssl_enabled')
rabbitmq_cert_public = ctx.node.properties('rabbitmq_cert_public')
rabbitmq_cert_private = ctx.node.properties('rabbitmq_cert_private')
rabbitmq_username = ctx.node.properties('rabbitmq_username')
rabbitmq_password = ctx.node.properties('rabbitmq_password')


def install_rabbitmq():
    ctx.logger.info("Installing RabbitMQ...")

    utils.set_selinux_permissive()

    utils.copy_notice('rabbitmq')

    utils.create_dir(rabbitmq_log_path)

    utils.yum_install(erlang_source_url)
    utils.yum_install(rabbitmq_source_url)

    utils.deploy_logrotate_config('rabbitmq')

    ctx.logger.info("Deploying rabbit stop script...")
    utils.deploy_blueprint_resource(
        os.path.join(config_path, 'kill-rabbit'),
        '/usr/local/bin/kill-rabbit',
    )
    utils.set_permissions_owner_execute_only('/usr/local/bin/kill-rabbit')

    utils.systemd.configure('rabbitmq')

    ctx.logger.info("Configuring file descriptors limit...")
    utils.deploy_blueprint_resource(
        os.path.join(config_path, 'rabbitmq_ulimit.conf'),
        '/etc/security/limits.d/rabbitmq.conf',
    )

    ctx.logger.info('Applying rabbitmq systemd service configuration...')
    utils.systemd.daemon_reload()

    ctx.logger.info('Correcting ownership of rabbitmq logs dir...')
    utils.chown(
        user='rabbitmq',
        group='rabbitmq',
        path=rabbitmq_log_path,
    )

    ctx.logger.info('Starting RabbitMQ service...')
    utils.systemd.enable('cloudify-rabbitmq.service')
    utils.systemd.start('cloudify-rabbitmq.service')

    set_up_users()

    ctx.logger.info('Enabling RabbitMQ plugins...')
    # We need to retry this occasionally if rabbit isn't ready in time
    utils.run(
        ['sudo', 'rabbitmq-plugins', 'enable', 'rabbitmq_management'],
        retries=5,
    )
    utils.run(
        ['sudo', 'rabbitmq-plugins', 'enable', 'rabbitmq_tracing'],
        retries=5,
    )

    ctx.logger.info("Setting RabbitMQ policies...")
    conf_message = 'Setting cloudify-{queue} queue {setting} to {amount}'
    ctx.logger.info(conf_message.format(
        queue='logs',
        setting='message-ttl',
        amount=rabbitmq_logs_queue_message_ttl,
    ))
    utils.run(
        [
            'sudo', 'rabbitmqctl', 'set_policy', 'logs_queue_message_ttl',
            '^cloudify-logs$',
            '{{"message-ttl":{limit}}}'.format(
                limit=rabbitmq_logs_queue_message_ttl,
            ),
            '--apply-to', 'queues',
        ],
        retries=5,
    )
    ctx.logger.info(conf_message.format(
        queue='events',
        setting='message-ttl',
        amount=rabbitmq_events_queue_message_ttl,
    ))
    utils.run(
        [
            'sudo', 'rabbitmqctl', 'set_policy', 'events_queue_message_ttl',
            '^cloudify-events$',
            '{{"message-ttl":{limit}}}'.format(
                limit=rabbitmq_events_queue_message_ttl,
            ),
            '--apply-to', 'queues',
        ],
        retries=5,
    )
    ctx.logger.info(conf_message.format(
        queue='monitoring',
        setting='message-ttl',
        amount=rabbitmq_metrics_queue_message_ttl,
    ))
    utils.run(
        [
            'sudo', 'rabbitmqctl', 'set_policy', 'metrics_queue_message_ttl',
            '^amq\.gen.*$',
            '{{"message-ttl":{limit}}}'.format(
                limit=rabbitmq_metrics_queue_message_ttl,
            ),
            '--apply-to', 'queues',
        ],
        retries=5,
    )
    utils.run(
        [
            'sudo', 'rabbitmqctl', 'set_policy',
            'riemann_deployment_queues_message_ttl',
            '^.*-riemann$',
            '{{"message-ttl":{limit}}}'.format(
                limit=rabbitmq_metrics_queue_message_ttl,
            ),
            '--apply-to', 'queues',
        ],
        retries=5,
    )
    ctx.logger.info(conf_message.format(
        queue='logs',
        setting='queue length',
        amount=rabbitmq_logs_queue_length_limit,
    ))
    utils.run(
        [
            'sudo', 'rabbitmqctl', 'set_policy', 'logs_queue_length',
            '^cloudify-logs$',
            '{{"max-length":{limit}}}'.format(
                limit=rabbitmq_logs_queue_length_limit,
            ),
            '--apply-to', 'queues',
        ],
        retries=5,
    )
    ctx.logger.info(conf_message.format(
        queue='events',
        setting='queue length',
        amount=rabbitmq_events_queue_length_limit,
    ))
    utils.run(
        [
            'sudo', 'rabbitmqctl', 'set_policy', 'events_queue_length',
            '^cloudify-events$',
            '{{"max-length":{limit}}}'.format(
                limit=rabbitmq_events_queue_length_limit,
            ),
            '--apply-to', 'queues',
        ],
        retries=5,
    )
    ctx.logger.info(conf_message.format(
        queue='monitoring',
        setting='queue length',
        amount=rabbitmq_metrics_queue_length_limit,
    ))
    utils.run(
        [
            'sudo', 'rabbitmqctl', 'set_policy', 'metrics_queue_length',
            '^amq\.gen.*$',
            '{{"max-length":{limit}}}'.format(
                limit=rabbitmq_metrics_queue_length_limit,
            ),
            '--apply-to', 'queues',
        ],
        retries=5,
    )
    utils.run(
        [
            'sudo', 'rabbitmqctl', 'set_policy',
            'riemann_deployment_queues_length',
            '^.*-riemann$',
            '{{"max-length":{limit}}}'.format(
                limit=rabbitmq_metrics_queue_length_limit,
            ),
            '--apply-to', 'queues',
        ],
        retries=5,
    )

    # Prepare to configure SSL/no-SSL
    utils.systemd.stop('cloudify-rabbitmq.service')

    if rabbitmq_ssl_enabled:
        configure_ssl()
        utils.deploy_blueprint_resource(
            os.path.join(config_path, 'rabbitmq.config-ssl'),
            '/etc/rabbitmq/rabbitmq.config',
        )
    else:
        if rabbitmq_cert_public != '' or rabbitmq_cert_private != '':
            ctx.logger.info(
                'Rabbit certificates supplied but rabbitmq_ssl_enabled is '
                'not set to true.',
                level='warn',
            )
        utils.deploy_blueprint_resource(
            os.path.join(config_path, 'rabbitmq.config-nossl'),
            '/etc/rabbitmq/rabbitmq.config',
        )


def set_up_users():
    ctx.logger.info('Disabling RabbitMQ guest user')
    utils.run(
        ['sudo', 'rabbitmqctl', 'clear_permissions', 'guest'],
        retries=5,
    )
    utils.run(
        ['sudo', 'rabbitmqctl', 'delete_user', 'guest'],
        retries=5
    )

    ctx.logger.info('Creating new RabbitMQ user and setting permissions...')
    utils.run(
        ['sudo', 'rabbitmqctl', 'add_user',
         rabbitmq_username, rabbitmq_password],
        retries=5
    )
    utils.run(
        ['sudo', 'rabbitmqctl', 'set_permissions',
         rabbitmq_username, '.*', '.*', '.*'],
        retries=5
    )


def configure_ssl():
    if rabbitmq_cert_public == '' or rabbitmq_cert_private == '':
        utils.error_exit('When SSL is enabled for RabbitMQ, '
                         'certificates must be supplied.')

    # Deploy will validate the certificates
    utils.deploy_ssl_certificate(
        destination='/etc/rabbitmq/rabbit-pub.pem',
        cert=rabbitmq_cert_public,
        group='rabbitmq',
    )
    utils.deploy_ssl_certificate(
        destination='/etc/rabbitmq/rabbit-priv.pem',
        cert=rabbitmq_cert_private,
        group='rabbitmq',
        private=True,
    )

if rabbitmq_endpoint_ip == '':
    broker_ip = ctx.instance.host_ip()
    ctx.logger.info("Installing rabbitmq on manager")
    install_rabbitmq()
else:
    broker_ip = rabbitmq_endpoint_ip
    ctx.logger.info("Using external rabbitmq at {ip}".format(
        ip=broker_ip,
    ))
    utils.error_exit('#%s#' % broker_ip)

ctx.logger.info("Setting Broker IP runtime property to {ip}.".format(
    ip=broker_ip,
))
ctx.instance.runtime_properties('rabbitmq_endpoint_ip', value=broker_ip)

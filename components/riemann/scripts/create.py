#!/usr/bin/env python

import subprocess
import os
import importlib

subprocess.check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')


CONFIG_PATH = 'components/riemann/config'

LANGOHR_SOURCE_URL = ctx.node.properties('langohr_jar_source_url')
DAEMONIZE_SOURCE_URL = ctx.node.properties('daemonize_rpm_source_url')
RIEMANN_SOURCE_URL = ctx.node.properties('riemann_rpm_source_url')
# Needed for Riemann's config
CLOUDIFY_RESOURCES_URL = ctx.node.properties('cloudify_resources_url')
RABBITMQ_USERNAME = ctx.node.properties('rabbitmq_username')
RABBITMQ_PASSWORD = ctx.node.properties('rabbitmq_password')

RIEMANN_CONFIG_PATH = '/etc/riemann'
RIEMANN_LOG_PATH = '/var/log/cloudify/riemann'
LANGOHR_HOME = '/opt/lib'
EXTRA_CLASSPATH = '{0}/langohr.jar'.format(LANGOHR_HOME)


# Confirm username and password have been supplied for broker before continuing
# Components other than logstash and riemann have this handled in code already
# Note that these are not directly used in this script, but are used by the
# deployed resources, hence the check here.
if not RABBITMQ_USERNAME or not RABBITMQ_PASSWORD:
    utils.error_exit(
        'Both rabbitmq_username and rabbitmq_password must be supplied and at '
        'least 1 character long in the manager blueprint inputs.')

ctx.instance.runtime_properties(
    'rabbitmq_endpoint_ip', value=utils.get_rabbitmq_endpoint_ip())

ctx.logger.info('Installing Riemann...')
utils.set_selinux_permissive()

utils.copy_notice('riemann')
utils.create_dir(RIEMANN_LOG_PATH)
utils.create_dir(LANGOHR_HOME)
utils.create_dir(RIEMANN_CONFIG_PATH)
utils.create_dir('{0}/conf.d'.format(RIEMANN_CONFIG_PATH))

langohr = utils.download_cloudify_resource(LANGOHR_SOURCE_URL)
utils.sudo(['cp', langohr, EXTRA_CLASSPATH])
ctx.logger.info('Applying Langohr permissions...')
utils.sudo(['chmod', '644', EXTRA_CLASSPATH])
ctx.logger.info('Installing Daemonize...')
utils.yum_install(DAEMONIZE_SOURCE_URL)
utils.yum_install(RIEMANN_SOURCE_URL)

utils.deploy_logrotate_config('riemann')

ctx.logger.info('Downloading cloudify-manager Repository...')
manager_repo = utils.download_cloudify_resource(CLOUDIFY_RESOURCES_URL)
ctx.logger.info('Extracting Manager Repository...')
utils.extract_github_archive_to_tmp(manager_repo)
ctx.logger.info('Deploying Riemann manager.config...')
utils.move(
    '/tmp/plugins/riemann-controller/riemann_controller/resources/manager.config',  # NOQA
    '{0}/conf.d/manager.config"'.format(RIEMANN_CONFIG_PATH))

ctx.logger.info('Deploying Riemann conf...')
utils.deploy_blueprint_resource(
    '{0}/main.clj'.format(CONFIG_PATH),
    '{0}/main.clj'.format(RIEMANN_CONFIG_PATH))

# our riemann configuration will (by default) try to read these environment
# variables. If they don't exist, it will assume
# that they're found at "localhost"
# export MANAGEMENT_IP=""
# export RABBITMQ_HOST=""

# we inject the management_ip for both of these to Riemann's systemd config.
# These should be potentially different
# if the manager and rabbitmq are running on different hosts.
utils.systemd.configure('riemann')
utils.clean_var_log_dir('riemann')

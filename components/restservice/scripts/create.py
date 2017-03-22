#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


REST_RESOURCES_PATH = 'resources/rest'

# TODO: change to /opt/cloudify-rest-service
REST_SERVICE_HOME = '/opt/manager'
REST_SERVICE_NAME = 'restservice'
CLOUDIFY_AGENT_DIR = 'cloudify_agent'

ctx_properties = utils.ctx_factory.create(REST_SERVICE_NAME)


def install_optional(rest_venv):
    props = ctx_properties

    dsl_parser_source_url = props['dsl_parser_module_source_url']
    rest_client_source_url = props['rest_client_module_source_url']
    plugins_common_source_url = props['plugins_common_module_source_url']
    script_plugin_source_url = props['script_plugin_module_source_url']
    agent_source_url = props['agent_module_source_url']

    rest_service_source_url = props['rest_service_module_source_url']

    # this allows to upgrade modules if necessary.
    ctx.logger.info('Installing Optional Packages if supplied...')
    if dsl_parser_source_url:
        utils.install_python_package(dsl_parser_source_url, rest_venv)
    if rest_client_source_url:
        utils.install_python_package(rest_client_source_url, rest_venv)
    if plugins_common_source_url:
        utils.install_python_package(plugins_common_source_url, rest_venv)
    if script_plugin_source_url:
        utils.install_python_package(script_plugin_source_url, rest_venv)
    if agent_source_url:
        utils.install_python_package(agent_source_url, rest_venv)

    if rest_service_source_url:
        ctx.logger.info('Downloading cloudify-manager Repository...')
        manager_repo = \
            utils.download_cloudify_resource(rest_service_source_url,
                                             REST_SERVICE_NAME)
        ctx.logger.info('Extracting Manager Repository...')
        utils.untar(manager_repo)

        ctx.logger.info('Installing REST Service...')
        utils.install_python_package('/tmp/rest-service', rest_venv)
        ctx.logger.info('Deploying Required Manager Resources...')
        utils.move(
            '/tmp/resources/rest-service/cloudify/',
            utils.MANAGER_RESOURCES_HOME
        )


def deploy_broker_configuration():
    # injected as an input to the script
    rabbit_props = utils.ctx_factory.get('rabbitmq')
    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = \
        utils.get_rabbitmq_endpoint_ip()

    ctx.instance.runtime_properties['rabbitmq_ssl_enabled'] = True
    ctx.instance.runtime_properties['rabbitmq_username'] = \
        rabbit_props.get('rabbitmq_username')
    ctx.instance.runtime_properties['rabbitmq_password'] = \
        rabbit_props.get('rabbitmq_password')

    ctx.logger.info('Retrieving postgresql input configuration')
    postgresql_props = utils.ctx_factory.get('postgresql-9.5')
    ctx.instance.runtime_properties['postgresql_db_name'] = \
        postgresql_props.get('postgresql_db_name')
    ctx.instance.runtime_properties['postgresql_host'] = \
        postgresql_props.get('postgresql_host')

    # Add certificate and select port, as applicable
    ctx.instance.runtime_properties['broker_cert_path'] = \
        utils.INTERNAL_CERT_PATH
    # Use SSL port
    ctx.instance.runtime_properties['broker_port'] = 5671


def _configure_dbus(rest_venv):
    # link dbus-python-1.1.1-9.el7.x86_64 to the venv for `cfy status`
    # (module in pypi is very old)
    site_packages = 'lib64/python2.7/site-packages'
    dbus_relative_path = os.path.join(site_packages, 'dbus')
    dbuslib = os.path.join('/usr', dbus_relative_path)
    dbus_glib_bindings = os.path.join('/usr', site_packages,
                                      '_dbus_glib_bindings.so')
    dbus_bindings = os.path.join('/usr', site_packages, '_dbus_bindings.so')
    if os.path.isdir(dbuslib):
        dbus_venv_path = os.path.join(rest_venv, dbus_relative_path)
        if not os.path.islink(dbus_venv_path):
            utils.ln(source=dbuslib, target=dbus_venv_path, params='-sf')
            utils.ln(source=dbus_bindings, target=dbus_venv_path, params='-sf')
        if not os.path.islink(os.path.join(rest_venv, site_packages)):
            utils.ln(source=dbus_glib_bindings, target=os.path.join(
                    rest_venv, site_packages), params='-sf')
    else:
        ctx.logger.warn(
                'Could not find dbus install, cfy status will not work')


def install_restservice():
    rest_service_rpm_source_url = ctx_properties['rest_service_rpm_source_url']

    rest_venv = os.path.join(REST_SERVICE_HOME, 'env')
    rest_service_log_path = '/var/log/cloudify/rest'
    agent_dir = os.path.join(utils.MANAGER_RESOURCES_HOME, CLOUDIFY_AGENT_DIR)

    ctx.logger.info('Installing REST Service...')
    utils.set_selinux_permissive()

    utils.copy_notice(REST_SERVICE_NAME)
    utils.mkdir(REST_SERVICE_HOME)
    utils.mkdir(rest_service_log_path)
    utils.mkdir(utils.MANAGER_RESOURCES_HOME)
    utils.mkdir(agent_dir)

    deploy_broker_configuration()
    utils.yum_install(rest_service_rpm_source_url,
                      service_name=REST_SERVICE_NAME)
    _configure_dbus(rest_venv)
    install_optional(rest_venv)
    utils.logrotate(REST_SERVICE_NAME)


install_restservice()

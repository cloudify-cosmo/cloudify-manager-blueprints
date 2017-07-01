#!/usr/bin/env python

import os
from os.path import join, dirname, islink, isdir

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'restservice'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME

HOME_DIR = '/opt/manager'
LOG_DIR = join(utils.BASE_LOG_DIR, 'rest')
runtime_props['files_to_remove'] = [HOME_DIR, LOG_DIR]

# Used in the service template
runtime_props['home_dir'] = HOME_DIR
runtime_props['log_dir'] = LOG_DIR

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)


def install_optional(rest_venv):
    props = ctx_properties

    dsl_parser_source_url = props['dsl_parser_module_source_url']
    rest_client_source_url = props['rest_client_module_source_url']
    plugins_common_source_url = props['plugins_common_module_source_url']
    script_plugin_source_url = props['script_plugin_module_source_url']
    agent_source_url = props['agent_module_source_url']
    pip_constraints = props['pip_constraints']

    rest_service_source_url = props['rest_service_module_source_url']

    constraints_file = utils.write_to_tempfile(pip_constraints) \
        if pip_constraints else None

    # this allows to upgrade modules if necessary.
    ctx.logger.info('Installing Optional Packages if supplied...')

    if dsl_parser_source_url:
        utils.install_python_package(dsl_parser_source_url, rest_venv,
                                     constraints_file)
    if rest_client_source_url:
        utils.install_python_package(rest_client_source_url, rest_venv,
                                     constraints_file)
    if plugins_common_source_url:
        utils.install_python_package(plugins_common_source_url, rest_venv,
                                     constraints_file)
    if script_plugin_source_url:
        utils.install_python_package(script_plugin_source_url, rest_venv,
                                     constraints_file)
    if agent_source_url:
        utils.install_python_package(agent_source_url, rest_venv,
                                     constraints_file)

    if rest_service_source_url:
        ctx.logger.info('Downloading cloudify-manager Repository...')
        manager_repo = \
            utils.download_cloudify_resource(rest_service_source_url,
                                             SERVICE_NAME)
        ctx.logger.info('Extracting Manager Repository...')
        tmp_dir = utils.untar(manager_repo, unique_tmp_dir=True)
        rest_service_dir = join(tmp_dir, 'rest-service')
        resources_dir = join(tmp_dir, 'resources/rest-service/cloudify/')

        ctx.logger.info('Installing REST Service...')
        utils.install_python_package(rest_service_dir, rest_venv,
                                     constraints_file)

        ctx.logger.info('Deploying Required Manager Resources...')
        utils.move(resources_dir, utils.MANAGER_RESOURCES_HOME)

        utils.remove(tmp_dir)

    if constraints_file:
        os.remove(constraints_file)


def deploy_broker_configuration():
    # injected as an input to the script
    rabbit_props = utils.ctx_factory.get('rabbitmq')
    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = \
        utils.get_rabbitmq_endpoint_ip()

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
    ctx.instance.runtime_properties['broker_cert_path'] = \
        utils.INTERNAL_CERT_PATH


def _configure_dbus(rest_venv):
    # link dbus-python-1.1.1-9.el7.x86_64 to the venv for `cfy status`
    # (module in pypi is very old)
    site_packages = 'lib64/python2.7/site-packages'
    dbus_relative_path = join(site_packages, 'dbus')
    dbuslib = join('/usr', dbus_relative_path)
    dbus_glib_bindings = join('/usr', site_packages, '_dbus_glib_bindings.so')
    dbus_bindings = join('/usr', site_packages, '_dbus_bindings.so')
    if isdir(dbuslib):
        dbus_venv_path = join(rest_venv, dbus_relative_path)
        if not islink(dbus_venv_path):
            utils.ln(source=dbuslib, target=dbus_venv_path, params='-sf')
            utils.ln(source=dbus_bindings, target=dbus_venv_path, params='-sf')
        if not islink(join(rest_venv, site_packages)):
            utils.ln(source=dbus_glib_bindings, target=join(
                    rest_venv, site_packages), params='-sf')
    else:
        ctx.logger.warn(
                'Could not find dbus install, cfy status will not work')


def install_restservice():
    utils.set_service_as_cloudify_service(runtime_props)
    rest_service_rpm_source_url = ctx_properties['rest_service_rpm_source_url']

    rest_venv = join(HOME_DIR, 'env')
    agent_dir = join(utils.MANAGER_RESOURCES_HOME, 'cloudify_agent')

    ctx.logger.info('Installing REST Service...')
    utils.set_selinux_permissive()

    utils.copy_notice(SERVICE_NAME)
    utils.mkdir(HOME_DIR)
    utils.mkdir(LOG_DIR)
    utils.chown(utils.CLOUDIFY_USER, utils.CLOUDIFY_GROUP, LOG_DIR)
    utils.mkdir(utils.MANAGER_RESOURCES_HOME)
    utils.mkdir(agent_dir)

    deploy_broker_configuration()
    utils.yum_install(rest_service_rpm_source_url,
                      service_name=SERVICE_NAME)
    _configure_dbus(rest_venv)
    install_optional(rest_venv)
    utils.logrotate(SERVICE_NAME)

    utils.deploy_sudo_command_script(
        script='/usr/bin/systemctl',
        description='Run systemctl'
    )
    utils.deploy_sudo_command_script(
        script='/usr/sbin/shutdown',
        description='Perform shutdown (reboot)'
    )


install_restservice()

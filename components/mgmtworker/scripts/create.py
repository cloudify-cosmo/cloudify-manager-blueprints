#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'mgmtworker'
AMQP_SSL_PORT = '5671'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME

HOME_DIR = join('/opt', SERVICE_NAME)
LOG_DIR = join(utils.BASE_LOG_DIR, SERVICE_NAME)
runtime_props['files_to_remove'] = [HOME_DIR, LOG_DIR]

# Used in the service template
runtime_props['home_dir'] = HOME_DIR
runtime_props['log_dir'] = LOG_DIR
CLOUDIFY_USER = utils.CLOUDIFY_USER
CLOUDIFY_GROUP = utils.CLOUDIFY_GROUP

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)


def _install_optional(mgmtworker_venv):
    rest_props = utils.ctx_factory.get('restservice')
    rest_client_source_url = rest_props['rest_client_module_source_url']
    plugins_common_source_url = rest_props['plugins_common_module_source_url']
    script_plugin_source_url = rest_props['script_plugin_module_source_url']
    rest_service_source_url = rest_props['rest_service_module_source_url']
    agent_source_url = rest_props['agent_module_source_url']
    pip_constraints = rest_props['pip_constraints']

    constraints_file = utils.write_to_tempfile(pip_constraints) if \
        pip_constraints else None

    # this allows to upgrade modules if necessary.
    ctx.logger.info('Installing Optional Packages if supplied...')
    if rest_client_source_url:
        utils.install_python_package(rest_client_source_url, mgmtworker_venv,
                                     constraints_file)
    if plugins_common_source_url:
        utils.install_python_package(
            plugins_common_source_url, mgmtworker_venv,
            constraints_file)
    if script_plugin_source_url:
        utils.install_python_package(script_plugin_source_url, mgmtworker_venv,
                                     constraints_file)
    if agent_source_url:
        utils.install_python_package(agent_source_url, mgmtworker_venv,
                                     constraints_file)

    if rest_service_source_url:
        ctx.logger.info('Downloading cloudify-manager Repository...')
        manager_repo = \
            utils.download_cloudify_resource(rest_service_source_url,
                                             SERVICE_NAME)

        ctx.logger.info('Extracting Manager Repository...')
        tmp_dir = utils.untar(manager_repo, unique_tmp_dir=True)
        workflows_dir = join(tmp_dir, 'workflows')
        riemann_dir = join(tmp_dir, 'plugins/riemann-controller')

        ctx.logger.info('Installing Management Worker Plugins...')
        utils.install_python_package(riemann_dir, mgmtworker_venv,
                                     constraints_file)
        utils.install_python_package(workflows_dir, mgmtworker_venv,
                                     constraints_file)

        utils.remove(tmp_dir)

    if constraints_file:
        os.remove(constraints_file)


def install_mgmtworker():
    riemann_dir = '/opt/riemann'

    management_worker_rpm_source_url = \
        ctx_properties['management_worker_rpm_source_url']

    runtime_props['rabbitmq_endpoint_ip'] = utils.get_rabbitmq_endpoint_ip()

    # Fix possible injections in json of rabbit credentials
    # See json.org for string spec
    for key in ['rabbitmq_username', 'rabbitmq_password']:
        # We will not escape newlines or other control characters,
        # we will accept them breaking
        # things noisily, e.g. on newlines and backspaces.
        # TODO: add:
        # sed 's/"/\\"/' | sed 's/\\/\\\\/' | sed s-/-\\/- | sed 's/\t/\\t/'
        runtime_props[key] = ctx_properties[key]

    utils.set_service_as_cloudify_service(runtime_props)

    ctx.logger.info('Installing Management Worker...')
    utils.set_selinux_permissive()

    utils.copy_notice(SERVICE_NAME)
    utils.mkdir(HOME_DIR)
    utils.mkdir(join(HOME_DIR, 'config'))
    utils.mkdir(join(HOME_DIR, 'work'))
    utils.mkdir(LOG_DIR)
    utils.mkdir(riemann_dir)

    mgmtworker_venv = join(HOME_DIR, 'env')

    # this create the mgmtworker_venv and installs the relevant
    # modules into it.
    utils.yum_install(management_worker_rpm_source_url,
                      service_name=SERVICE_NAME)
    _install_optional(mgmtworker_venv)

    # Add certificate and select port, as applicable
    runtime_props['broker_cert_path'] = utils.INTERNAL_CERT_PATH
    # Use SSL port
    runtime_props['broker_port'] = AMQP_SSL_PORT

    utils.chown(CLOUDIFY_USER, CLOUDIFY_GROUP, HOME_DIR)
    utils.chown(CLOUDIFY_USER, CLOUDIFY_GROUP, LOG_DIR)
    # Changing perms on workdir and venv in case they are put outside homedir
    utils.chown(CLOUDIFY_USER, CLOUDIFY_GROUP, mgmtworker_venv)
    # Prepare riemann dir. We will change the owner to riemann later, but the
    # management worker will still need access to it
    utils.chown(CLOUDIFY_USER, CLOUDIFY_GROUP, riemann_dir)
    utils.chmod('770', riemann_dir)

    ctx.logger.info("Using broker port: {0}".format(
        ctx.instance.runtime_properties['broker_port']))


install_mgmtworker()

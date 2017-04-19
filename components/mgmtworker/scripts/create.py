#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


MGMT_WORKER_SERVICE_NAME = 'mgmtworker'

ctx_properties = utils.ctx_factory.create(MGMT_WORKER_SERVICE_NAME)
MGMTWORKER_USER = ctx_properties['os_user']
MGMTWORKER_GROUP = ctx_properties['os_group']
HOMEDIR = ctx_properties['os_homedir']


def _install_optional(mgmtworker_venv):

    rest_props = utils.ctx_factory.get('restservice')
    dsl_parser_source_url = \
        rest_props['dsl_parser_module_source_url']
    rest_client_source_url = \
        rest_props['rest_client_module_source_url']
    plugins_common_source_url = \
        rest_props['plugins_common_module_source_url']
    script_plugin_source_url = \
        rest_props['script_plugin_module_source_url']
    rest_service_source_url = \
        rest_props['rest_service_module_source_url']
    agent_source_url = \
        rest_props['agent_module_source_url']

    # this allows to upgrade modules if necessary.
    ctx.logger.info('Installing Optional Packages if supplied...')
    if dsl_parser_source_url:
        utils.install_python_package(dsl_parser_source_url, mgmtworker_venv)
    if rest_client_source_url:
        utils.install_python_package(rest_client_source_url, mgmtworker_venv)
    if plugins_common_source_url:
        utils.install_python_package(
            plugins_common_source_url, mgmtworker_venv)
    if script_plugin_source_url:
        utils.install_python_package(script_plugin_source_url, mgmtworker_venv)
    if agent_source_url:
        utils.install_python_package(agent_source_url, mgmtworker_venv)

    if rest_service_source_url:
        ctx.logger.info('Downloading cloudify-manager Repository...')
        manager_repo = \
            utils.download_cloudify_resource(rest_service_source_url,
                                             MGMT_WORKER_SERVICE_NAME)
        ctx.logger.info('Extracting Manager Repository...')
        utils.untar(manager_repo)

        ctx.logger.info('Installing Management Worker Plugins...')
        # shouldn't we extract the riemann-controller and workflows modules to
        # their own repos?
        utils.install_python_package(
            '/tmp/plugins/riemann-controller', mgmtworker_venv)
        utils.install_python_package('/tmp/workflows', mgmtworker_venv)


def install_mgmtworker():

    management_worker_rpm_source_url = \
        ctx_properties['management_worker_rpm_source_url']

    # these must all be exported as part of the start operation.
    # they will not persist, so we should use the new agent
    # don't forget to change all localhosts to the relevant ips
    mgmtworker_home = '/opt/mgmtworker'
    mgmtworker_venv = '{0}/env'.format(mgmtworker_home)
    celery_work_dir = '{0}/work'.format(mgmtworker_home)
    celery_log_dir = "/var/log/cloudify/mgmtworker"

    ctx.instance.runtime_properties['rabbitmq_endpoint_ip'] = \
        utils.get_rabbitmq_endpoint_ip()

    # Fix possible injections in json of rabbit credentials
    # See json.org for string spec
    for key in ['rabbitmq_username', 'rabbitmq_password']:
        # We will not escape newlines or other control characters,
        # we will accept them breaking
        # things noisily, e.g. on newlines and backspaces.
        # TODO: add:
        # sed 's/"/\\"/' | sed 's/\\/\\\\/' | sed s-/-\\/- | sed 's/\t/\\t/'
        ctx.instance.runtime_properties[key] = ctx_properties[key]

    # Make the ssl enabled flag work with json (boolean in lower case)
    # TODO: check if still needed:
    # broker_ssl_enabled = "$(echo ${rabbitmq_ssl_enabled} | tr '[:upper:]' '[:lower:]')"  # NOQA
    ctx.instance.runtime_properties['rabbitmq_ssl_enabled'] = True

    ctx.logger.info('Installing Management Worker...')
    utils.set_selinux_permissive()

    utils.copy_notice(MGMT_WORKER_SERVICE_NAME)
    utils.mkdir(mgmtworker_home)
    utils.mkdir('{0}/config'.format(mgmtworker_home))
    utils.mkdir(celery_log_dir)
    utils.mkdir(celery_work_dir)

    # this create the mgmtworker_venv and installs the relevant
    # modules into it.
    utils.yum_install(management_worker_rpm_source_url,
                      service_name=MGMT_WORKER_SERVICE_NAME)
    _install_optional(mgmtworker_venv)

    # Add certificate and select port, as applicable
    ctx.instance.runtime_properties['broker_cert_path'] = \
        utils.INTERNAL_CERT_PATH
    # Use SSL port
    ctx.instance.runtime_properties['broker_port'] = '5671'

    utils.create_service_user(
        user=MGMTWORKER_USER,
        home=HOMEDIR,
        group=MGMTWORKER_GROUP,
    )
    utils.chown(MGMTWORKER_USER, MGMTWORKER_GROUP, mgmtworker_home)
    utils.chown(MGMTWORKER_USER, MGMTWORKER_GROUP, celery_log_dir)
    # Changing perms on workdir and venv in case they are put outside homedir
    utils.chown(MGMTWORKER_USER, MGMTWORKER_GROUP, mgmtworker_venv)
    utils.chown(MGMTWORKER_USER, MGMTWORKER_GROUP, celery_work_dir)

    ctx.logger.info("broker_port: {0}".format(
        ctx.instance.runtime_properties['broker_port']))


install_mgmtworker()

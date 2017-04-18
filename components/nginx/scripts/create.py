#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'nginx'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME

LOG_DIR = join(utils.BASE_LOG_DIR, SERVICE_NAME)
UNIT_OVERRIDE_PATH = '/etc/systemd/system/nginx.service.d'
runtime_props['files_to_remove'] = [LOG_DIR, UNIT_OVERRIDE_PATH]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)
CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)
AGENTS_ROLLBACK_PATH = '/opt/cloudify/nginx/rollback_agents'


def install_nginx():
    nginx_source_url = ctx_properties['nginx_rpm_source_url']

    # this is a bit tricky. the rest_service_source_url contains files that
    # should be deployed in the fileserver. the thing is, that since the
    # rest service and nginx cannot be distributed between vms right now
    # anyway, these resources are deployed by the rest service node instead.
    # rest_service_source_url = \
    #     ctx.node.properties['rest_service_module_source_url']

    manager_resources_home = utils.MANAGER_RESOURCES_HOME
    manager_agents_path = utils.AGENT_ARCHIVES_PATH
    # TODO: check if can remove these two (should come with the agent package)
    manager_scripts_path = '{0}/packages/scripts'.format(
        manager_resources_home)
    manager_templates_path = '{0}/packages/templates'.format(
        manager_resources_home)

    # this is propagated to the agent retrieval script later on so that it's
    # not defined twice.
    ctx.instance.runtime_properties['agent_packages_path'] = \
        manager_agents_path

    # TODO: can we use static (not runtime) attributes for some of these?
    # how to set them?
    ctx.instance.runtime_properties['default_rest_service_port'] = '8100'

    ctx.logger.info('Installing Nginx...')
    utils.set_selinux_permissive()

    utils.copy_notice(SERVICE_NAME)
    utils.mkdir(LOG_DIR)
    utils.mkdir(manager_resources_home)

    utils.mkdir(manager_agents_path)
    # TODO: check if can remove these two (should come with the agent package)
    utils.mkdir(manager_scripts_path)
    utils.mkdir(manager_templates_path)
    utils.mkdir(UNIT_OVERRIDE_PATH)

    utils.yum_install(nginx_source_url, service_name=SERVICE_NAME)

    ctx.logger.info('Creating systemd unit override...')
    utils.deploy_blueprint_resource(
        '{0}/restart.conf'.format(CONFIG_PATH),
        '{0}/restart.conf'.format(UNIT_OVERRIDE_PATH),
        SERVICE_NAME)

    utils.logrotate(SERVICE_NAME)
    utils.clean_var_log_dir(SERVICE_NAME)


install_nginx()

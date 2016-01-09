#!/usr/bin/env python

from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


CONFIG_PATH = 'components/nginx/config'


def install_nginx():
    nginx_source_url = ctx.node.properties['nginx_rpm_source_url']

    # unused?
    # rest_service_source_url = \
    #     ctx.node.properties['rest_service_module_source_url']

    nginx_log_path = '/var/log/cloudify/nginx'
    manager_resources_home = '/opt/manager/resources'
    manager_agents_path = '{0}/packages/agents'.format(manager_resources_home)
    manager_scripts_path = '{0}/packages/scripts'.format(
        manager_resources_home)
    manager_templates_path = '{0}/packages/templates'.format(
        manager_resources_home)
    nginx_unit_override = '/etc/systemd/system/nginx.service.d'

    # this is propagated to the agent retrieval script later on so that it's
    # not defined twice.
    ctx.instance.runtime_properties['agent_packages_path'] = \
        manager_agents_path

    # TODO can we use static (not runtime) attributes for some of these? how to
    # set them?
    ctx.instance.runtime_properties['default_rest_service_port'] = '8100'
    ctx.instance.runtime_properties['internal_rest_service_port'] = '8101'

    ctx.logger.info('Installing Nginx...')
    utils.set_selinux_permissive()

    utils.copy_notice('nginx')
    utils.create_dir(nginx_log_path)
    utils.create_dir(manager_resources_home)

    utils.create_dir(manager_agents_path)
    utils.create_dir(manager_scripts_path)
    utils.create_dir(manager_templates_path)

    utils.create_dir(nginx_unit_override)

    utils.yum_install(nginx_source_url)

    ctx.logger.info('Creating systemd unit override...')
    utils.deploy_blueprint_resource(
        '{0}/restart.conf'.format(CONFIG_PATH),
        '{0}/restart.conf'.format(nginx_unit_override))

    utils.deploy_logrotate_config('nginx')
    utils.clean_var_log_dir('nginx')


install_nginx()

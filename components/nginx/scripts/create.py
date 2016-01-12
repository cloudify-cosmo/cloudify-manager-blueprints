#!/usr/bin/env python

from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


CONFIG_PATH = 'components/nginx/config'


def install_nginx():
    nginx_source_url = ctx.node.properties['nginx_rpm_source_url']

    # this is a bit tricky. the rest_service_source_url contains files that
    # should be deployed in the fileserver. the thing is, that since the
    # rest service and nginx cannot be distributed between vms right now
    # anyway, these resources are deployed by the rest service node instead.
    # rest_service_source_url = \
    #     ctx.node.properties['rest_service_module_source_url']

    nginx_log_path = '/var/log/cloudify/nginx'
    manager_resources_home = '/opt/manager/resources'
    manager_agents_path = '{0}/packages/agents'.format(manager_resources_home)
    # TODO: check if can remove these two (should come with the agent package)
    manager_scripts_path = '{0}/packages/scripts'.format(
        manager_resources_home)
    manager_templates_path = '{0}/packages/templates'.format(
        manager_resources_home)
    nginx_unit_override = '/etc/systemd/system/nginx.service.d'

    # this is propagated to the agent retrieval script later on so that it's
    # not defined twice.
    ctx.instance.runtime_properties['agent_packages_path'] = \
        manager_agents_path

    # TODO: can we use static (not runtime) attributes for some of these?
    # how to set them?
    ctx.instance.runtime_properties['default_rest_service_port'] = 8100
    ctx.instance.runtime_properties['internal_rest_service_port'] = 8101

    ctx.logger.info('Installing Nginx...')
    utils.set_selinux_permissive()

    utils.copy_notice('nginx')
    utils.mkdir(nginx_log_path)
    utils.mkdir(manager_resources_home)

    utils.mkdir(manager_agents_path)
    # TODO: check if can remove these two (should come with the agent package)
    utils.mkdir(manager_scripts_path)
    utils.mkdir(manager_templates_path)
    utils.mkdir(nginx_unit_override)

    utils.yum_install(nginx_source_url)

    ctx.logger.info('Creating systemd unit override...')
    utils.deploy_blueprint_resource(
        '{0}/restart.conf'.format(CONFIG_PATH),
        '{0}/restart.conf'.format(nginx_unit_override))

    utils.logrotate('nginx')
    utils.clean_var_log_dir('nginx')


install_nginx()

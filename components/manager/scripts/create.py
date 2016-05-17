#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

NODE_NAME = 'manager-resources'

ctx_properties = utils.ctx_factory.create(NODE_NAME)

AGENTS_ROLLBACK_PATH = '/opt/cloudify/manager-resources/agents_rollback'


def deploy_manager_sources():
    """Deploys all manager sources from a single archive.
    """
    archive_path = ctx.node.properties['manager_resources_package']
    archive_checksum_path = \
        ctx.node.properties['manager_resources_package_checksum_file']
    skip_checksum_validation = ctx.node.properties['skip_checksum_validation']
    agent_archives_path = utils.AGENT_ARCHIVES_PATH
    utils.mkdir(agent_archives_path)
    if archive_path:
        sources_agents_path = os.path.join(
                utils.CLOUDIFY_SOURCES_PATH, 'agents')
        # this will leave this several hundreds of MBs archive on the
        # manager. should find a way to clean it after all operations
        # were completed and bootstrap succeeded as it is not longer
        # necessary
        utils.mkdir(utils.CLOUDIFY_SOURCES_PATH)
        res_name = os.path.basename(archive_path)
        destination = os.path.join(utils.CLOUDIFY_SOURCES_PATH, res_name)
        resources_archive_path = \
            utils.download_cloudify_resource(
                archive_path, NODE_NAME, destination=destination)
        # This would ideally go under utils.download_cloudify_resource but as
        # of now, we'll only be validating the manager resources package.

        if not skip_checksum_validation:
            skip_if_failed = False
            if not archive_checksum_path:
                skip_if_failed = True
                archive_checksum_path = archive_path + '.md5'
            md5_name = os.path.basename(archive_checksum_path)
            destination = os.path.join(utils.CLOUDIFY_SOURCES_PATH, md5_name)
            resources_archive_md5_path = utils.download_cloudify_resource(
                archive_checksum_path, NODE_NAME, destination=destination)
            if not utils.validate_md5_checksum(resources_archive_path,
                                               resources_archive_md5_path):
                    if skip_if_failed:
                        ctx.logger.warn('Checksum validation failed. '
                                        'Continuing as no checksum file was '
                                        'explicitly provided.')
                    else:
                        ctx.abort_operation(
                            'Failed to validate checksum for {0}'.format(
                                resources_archive_path))
            else:
                ctx.logger.info('Resources Package downloaded successfully...')
        else:
            ctx.logger.info(
                'Skipping resources package checksum validation...')

        utils.untar(
            resources_archive_path,
            utils.CLOUDIFY_SOURCES_PATH,
            skip_old_files=True)

        def splitext(filename):
            # not using os.path.splitext as it would return .gz instead of
            # .tar.gz
            if filename.endswith('.tar.gz'):
                return '.tar.gz'
            elif filename.endswith('.exe'):
                return '.exe'
            else:
                ctx.abort_operation(
                    'Unknown agent format for {0}. '
                    'Must be either tar.gz or exe'.format(filename))

        def normalize_agent_name(filename):
            # this returns the normalized name of an agent upon which our agent
            # installer retrieves agent packages for installation.
            # e.g. Ubuntu-trusty-agent_3.4.0-m3-b392.tar.gz returns
            # ubuntu-trusty-agent
            return filename.split('_', 1)[0].lower()

        def backup_agent_resources(agents_dir):
            ctx.logger.info('Backing up agents in {0}...'.format(agents_dir))
            if not os.path.exists(AGENTS_ROLLBACK_PATH):
                utils.mkdir(AGENTS_ROLLBACK_PATH)
                utils.copy(agents_dir, AGENTS_ROLLBACK_PATH)

        def restore_agent_resources(agents_dir):
            ctx.logger.info('Restoring agents in {0}'
                            .format(AGENTS_ROLLBACK_PATH))
            utils.remove(agents_dir)
            utils.mkdir(agents_dir)
            utils.copy(os.path.join(AGENTS_ROLLBACK_PATH, 'agents', '.'),
                       agents_dir)

        manager_resources_home = utils.MANAGER_RESOURCES_HOME

        manager_scripts_path = '{0}/packages/scripts'.format(
                manager_resources_home)
        manager_templates_path = '{0}/packages/templates'.format(
                manager_resources_home)
        if utils.is_upgrade:
            backup_agent_resources(agent_archives_path)
            if os.path.exists(agent_archives_path):
                utils.remove(agent_archives_path)
                utils.mkdir(agent_archives_path)
            if os.path.exists(manager_scripts_path):
                utils.remove(manager_scripts_path)
            ctx.logger.info('Upgrading agents...')
            if os.path.exists(manager_templates_path):
                utils.remove(manager_templates_path)
        elif utils.is_rollback:
            ctx.logger.info('Restoring agents...')
            restore_agent_resources(agent_archives_path)

        for agent_file in os.listdir(sources_agents_path):

            agent_id = normalize_agent_name(agent_file)
            agent_extension = splitext(agent_file)
            utils.move(
                os.path.join(sources_agents_path, agent_file),
                os.path.join(agent_archives_path, agent_id + agent_extension))


# def deploy_yamls():
#     def deploy_plugin_yaml(plugin, version):
#         plugin_dir = '{0}/spec/{1}-plugin/{2}/'.format(
#             utils.MANAGER_RESOURCES_HOME, plugin, version)
#         utils.mkdir(plugin_dir)
#         utils.deploy_blueprint_resource(
#             'resources/plugins/{0}-{1}-plugin.yaml',
#             os.path.join(plugin_dir, 'plugin.yaml'))

#     deploy_plugin_yaml('fabric', '1.4')
#     deploy_plugin_yaml('script', '1.4')
#     deploy_plugin_yaml('diamond', '1.3.2')
#     deploy_plugin_yaml('aws', '1.4')
#     deploy_plugin_yaml('openstack', '1.3.1')
#     deploy_plugin_yaml('tosca-vcloud', '1.3.1')
#     deploy_plugin_yaml('vsphere', '2.0')

#     types_yaml_dir = '{0}/spec/cloudify/3.4m4'.format(
#         utils.MANAGER_RESOURCES_HOME)
#     utils.mkdir()
#     utils.deploy_blueprint_resource(
#         'resources/types-3.4m4.yaml',
#         os.path.join(types_yaml_dir, 'types.yaml'))


deploy_manager_sources()

#!/usr/bin/env python

import os
import subprocess
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'stage'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME
STAGE_USER = '{0}_user'.format(SERVICE_NAME)
STAGE_GROUP = '{0}_group'.format(SERVICE_NAME)
runtime_props['service_user'] = STAGE_USER
runtime_props['service_group'] = STAGE_GROUP

HOME_DIR = join('/opt', 'cloudify-{0}'.format(SERVICE_NAME))
NODEJS_DIR = join('/opt', 'nodejs')
LOG_DIR = join(utils.BASE_LOG_DIR, SERVICE_NAME)
RESOURCES_DIR = join(HOME_DIR, 'resources')
runtime_props['home_dir'] = HOME_DIR
runtime_props['files_to_remove'] = [HOME_DIR, NODEJS_DIR, LOG_DIR]

ctx_properties = ctx.node.properties.get_all()
CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)


def _install_stage():
    nodejs_source_url = ctx_properties['nodejs_tar_source_url']
    stage_source_url = ctx_properties['stage_tar_source_url']

    if not utils.resource_factory.local_resource_exists(stage_source_url):
        ctx.logger.info('Stage package not found in manager resources '
                        'package. Stage will not be installed.')
        ctx.instance.runtime_properties['skip_installation'] = 'true'
        return

    # injected as an input to the script
    ctx.instance.runtime_properties['influxdb_endpoint_ip'] = \
        os.environ.get('INFLUXDB_ENDPOINT_IP')

    utils.set_selinux_permissive()
    utils.copy_notice(SERVICE_NAME)

    utils.mkdir(NODEJS_DIR)
    utils.mkdir(HOME_DIR)
    utils.mkdir(LOG_DIR)
    utils.mkdir(RESOURCES_DIR)

    utils.create_service_user(STAGE_USER, STAGE_GROUP, HOME_DIR)

    ctx.logger.info('Installing NodeJS...')
    nodejs = utils.download_cloudify_resource(nodejs_source_url, SERVICE_NAME)
    utils.untar(nodejs, NODEJS_DIR)
    utils.remove(nodejs)

    ctx.logger.info('Installing Cloudify Stage (UI)...')
    stage_tar = utils.download_cloudify_resource(stage_source_url,
                                                 SERVICE_NAME)
    if 'community' in stage_tar:
        ctx.logger.info('Community edition')
        ctx.instance.runtime_properties['community_mode'] = '-mode community'
    else:
        ctx.instance.runtime_properties['community_mode'] = ''

    utils.untar(stage_tar, HOME_DIR)
    utils.remove(stage_tar)

    ctx.logger.info('Fixing permissions...')
    utils.chown(STAGE_USER, STAGE_GROUP, HOME_DIR)
    utils.chown(STAGE_USER, STAGE_GROUP, NODEJS_DIR)
    utils.chown(STAGE_USER, STAGE_GROUP, LOG_DIR)
    configure_script(
        'restore-snapshot.py',
        'Restore stage directories from a snapshot path',
    )
    configure_script(
        'make-auth-token.py',
        'Update auth token for stage user',
    )
    # Allow snapshot restores to restore token
    utils.allow_user_to_sudo_command(
        '/opt/manager/env/bin/python',
        'Snapshot update auth token for stage user',
        allow_as=STAGE_USER,
    )
    subprocess.check_call([
        'sudo', '-u', 'stage_user',
        '/opt/manager/env/bin/python',
        '/opt/cloudify/stage/make-auth-token.py',
    ])

    utils.logrotate(SERVICE_NAME)
    utils.systemd.configure(SERVICE_NAME)

    backend_dir = join(HOME_DIR, 'backend')
    npm_path = join(NODEJS_DIR, 'bin', 'npm')
    subprocess.check_call(
            'cd {0}; {1} run db-migrate'.format(backend_dir, npm_path),
            shell=True)


def configure_script(script_name, description):
    utils.deploy_sudo_command_script(
        script_name,
        description,
        component=SERVICE_NAME,
        allow_as=STAGE_USER,
    )
    utils.chmod('a+rx', '/opt/cloudify/stage/' + script_name)
    utils.sudo(['usermod', '-aG', utils.CLOUDIFY_GROUP, STAGE_USER])


def main():
    _install_stage()


main()

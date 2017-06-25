#!/usr/bin/env python

import subprocess
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'composer'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME
COMPOSER_USER = '{0}_user'.format(SERVICE_NAME)
COMPOSER_GROUP = '{0}_group'.format(SERVICE_NAME)
runtime_props['service_user'] = COMPOSER_USER
runtime_props['service_group'] = COMPOSER_GROUP

HOME_DIR = join('/opt', 'cloudify-{0}'.format(SERVICE_NAME))
NODEJS_DIR = join('/opt', 'nodejs')
CLOUDIFY_SOURCES_PATH = '/opt/cloudify/sources'
LOG_DIR = join(utils.BASE_LOG_DIR, SERVICE_NAME)
runtime_props['home_dir'] = HOME_DIR
runtime_props['files_to_remove'] = [HOME_DIR, NODEJS_DIR, LOG_DIR]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)
CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)


def _install_composer():
    composer_source_url = ctx_properties['composer_tar_source_url']
    composer_filename = utils.get_file_name_from_url(composer_source_url)
    tmp_composer_source = utils.download_file(
        composer_source_url,
        '/tmp/{}'.format(composer_filename))
    composer_source_url = '{}/{}'.format(CLOUDIFY_SOURCES_PATH,
                                         composer_filename)

    utils.move(tmp_composer_source, composer_source_url)
    if not utils.resource_factory.local_resource_exists(composer_source_url):
        ctx.logger.info('Composer package not found in manager resources '
                        'package. Composer will not be installed.')
        ctx.logger.info("Yes")
        ctx.instance.runtime_properties['skip_installation'] = 'true'
        pass
        # return

    utils.set_selinux_permissive()
    utils.copy_notice(SERVICE_NAME)

    utils.mkdir(NODEJS_DIR)
    utils.mkdir(HOME_DIR)
    utils.mkdir(LOG_DIR)

    utils.create_service_user(COMPOSER_USER, COMPOSER_GROUP, HOME_DIR)

    ctx.logger.info('Installing Cloudify Composer...')
    composer_tar = utils.download_cloudify_resource(composer_source_url,
                                                    SERVICE_NAME)
    utils.untar(composer_tar, HOME_DIR)
    utils.remove(composer_tar)

    ctx.logger.info('Fixing permissions...')
    utils.chown(COMPOSER_USER, COMPOSER_GROUP, HOME_DIR)
    utils.chown(COMPOSER_USER, COMPOSER_GROUP, NODEJS_DIR)
    utils.chown(COMPOSER_USER, COMPOSER_GROUP, LOG_DIR)

    utils.logrotate(SERVICE_NAME)
    utils.systemd.configure(SERVICE_NAME)

    npm_path = join(NODEJS_DIR, 'bin', 'npm')
    subprocess.check_call(
        'cd {}; {} run db-migrate'.format(HOME_DIR, npm_path), shell=True)


def main():
    _install_composer()


main()

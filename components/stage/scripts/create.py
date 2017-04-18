#!/usr/bin/env python

import os
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

HOME_DIR = join('/opt', 'cloudify-{0}'.format(SERVICE_NAME))
NODEJS_DIR = join('/opt', 'nodejs')
LOG_DIR = join(utils.BASE_LOG_DIR, SERVICE_NAME)
runtime_props['files_to_remove'] = [HOME_DIR, NODEJS_DIR, LOG_DIR]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)
CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)


def install_stage():

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

    stage_user = 'stage'
    stage_group = 'stage'
    runtime_props['service_user'] = stage_user
    runtime_props['service_group'] = stage_group

    utils.set_selinux_permissive()

    utils.copy_notice(SERVICE_NAME)

    utils.mkdir(NODEJS_DIR)
    utils.mkdir(HOME_DIR)
    utils.mkdir(LOG_DIR)

    utils.create_service_user(stage_user, HOME_DIR)

    ctx.logger.info('Installing NodeJS...')
    nodejs = utils.download_cloudify_resource(nodejs_source_url, SERVICE_NAME)
    utils.untar(nodejs, NODEJS_DIR)
    utils.remove(nodejs)

    ctx.logger.info('Installing Cloudify Stage (UI)...')
    stage = utils.download_cloudify_resource(stage_source_url, SERVICE_NAME)
    utils.untar(stage, HOME_DIR)
    utils.remove(stage)

    ctx.logger.info('Fixing permissions...')
    utils.chown(stage_user, stage_group, HOME_DIR)
    utils.chown(stage_user, stage_group, NODEJS_DIR)
    utils.chown(stage_user, stage_group, LOG_DIR)

    utils.logrotate(SERVICE_NAME)
    utils.systemd.configure(SERVICE_NAME)


def main():
    install_stage()


main()

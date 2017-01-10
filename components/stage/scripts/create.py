#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

STAGE_SERVICE_NAME = 'stage'


CONFIG_PATH = 'components/stage/config'

ctx_properties = utils.ctx_factory.create(STAGE_SERVICE_NAME)


def install_stage():

    nodejs_source_url = ctx_properties['nodejs_tar_source_url']
    stage_source_url = ctx_properties['stage_tar_source_url']

    # injected as an input to the script
    ctx.instance.runtime_properties['influxdb_endpoint_ip'] = \
        os.environ.get('INFLUXDB_ENDPOINT_IP')

    nodejs_home = '/opt/nodejs'
    stage_home = '/opt/cloudify-stage'
    stage_log_path = '/var/log/cloudify/stage'

    stage_user = 'stage'
    stage_group = 'stage'

    utils.set_selinux_permissive()

    utils.copy_notice(STAGE_SERVICE_NAME)

    utils.mkdir(nodejs_home)
    utils.mkdir(stage_home)
    utils.mkdir(stage_log_path)

    utils.create_service_user(stage_user, stage_home)

    ctx.logger.info('Installing NodeJS...')
    nodejs = utils.download_cloudify_resource(nodejs_source_url,
                                              STAGE_SERVICE_NAME)
    utils.untar(nodejs, nodejs_home)

    ctx.logger.info('Installing Cloudify Stage (UI)...')
    stage = utils.download_cloudify_resource(stage_source_url,
                                             STAGE_SERVICE_NAME)
    utils.untar(stage, stage_home)

    ctx.logger.info('Fixing permissions...')
    utils.chown(stage_user, stage_group, stage_home)
    utils.chown(stage_user, stage_group, nodejs_home)
    utils.chown(stage_user, stage_group, stage_log_path)

    utils.logrotate(STAGE_SERVICE_NAME)
    utils.systemd.configure(STAGE_SERVICE_NAME)


def main():
    install_stage()


main()

#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'java'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME
LOG_DIR = join(utils.BASE_LOG_DIR, SERVICE_NAME)
runtime_props['files_to_remove'] = [LOG_DIR]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)


def install_java():
    java_source_url = ctx_properties['java_rpm_source_url']

    ctx.logger.info('Installing Java...')
    utils.set_selinux_permissive()
    utils.copy_notice(SERVICE_NAME)

    utils.yum_install(java_source_url, SERVICE_NAME)

    utils.mkdir(LOG_DIR)

    # Java install log is dropped in /var/log.
    # Move it to live with the rest of the cloudify logs
    java_install_log = '/var/log/java_install.log'
    if os.path.isfile(java_install_log):
        utils.move(java_install_log, LOG_DIR)


install_java()

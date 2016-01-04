#!/usr/bin/env python

import subprocess
import os
import importlib


subprocess.check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')

JAVA_SOURCE_URL = ctx.node.properties('java_rpm_source_url')


def install_java():
    ctx.logger.info('Installing Java...')
    utils.set_selinux_permissive()
    utils.copy_notice('java')

    utils.yum_install(JAVA_SOURCE_URL)

    # Make sure the cloudify logs dir exists before we try moving the java log
    # there -p will cause it not to error if the dir already exists
    utils.create_dir('/var/log/cloudify')

    # Java install log is dropped in /var/log.
    # Move it to live with the rest of the cloudify logs
    if os.path.isfile('/var/log/java_install.log'):
        utils.sudo('mv /var/log/java_install.log /var/log/cloudify')


install_java()

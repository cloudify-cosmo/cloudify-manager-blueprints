#!/usr/bin/env python

import subprocess
import os
import importlib


subprocess.check_output([
    'ctx', 'download-resource', 'components/utils.py',
    os.path.join(os.path.dirname(__file__), 'utils.py')])
ctx = utils = importlib.import_module('utils')

PIP_SOURCE_RPM_URL = ctx.node.properties('pip_source_rpm_url')
INSTALL_PYTHON_COMPILERS = ctx.node.properties('install_python_compilers')


def install_python_requirements():
    ctx.logger.info('Installing Python Requirements...')
    utils.set_selinux_permissive()
    utils.copy_notice('python')

    utils.yum_install(PIP_SOURCE_RPM_URL)

    if INSTALL_PYTHON_COMPILERS:
        ctx.logger.info('Installing Compilers...')
        utils.yum_install('python-devel')
        utils.yum_install('gcc')


install_python_requirements()

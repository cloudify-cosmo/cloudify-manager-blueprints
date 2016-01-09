#!/usr/bin/env python

from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


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

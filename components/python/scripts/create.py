#!/usr/bin/env python

from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


def install_python_requirements():

    pip_source_rpm_url = ctx.node.properties['pip_source_rpm_url']
    install_python_compilers = ctx.node.properties['install_python_compilers']

    ctx.logger.info('Installing Python Requirements...')
    utils.set_selinux_permissive()
    utils.copy_notice('python')

    utils.yum_install(pip_source_rpm_url)

    if install_python_compilers:
        ctx.logger.info('Installing Compilers...')
        utils.yum_install('python-devel')
        utils.yum_install('gcc')
        utils.yum_install('gcc-c++')


install_python_requirements()

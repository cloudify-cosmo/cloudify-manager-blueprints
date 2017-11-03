#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

ctx_properties = ctx.node.properties.get_all()


def install_python_requirements():

    pip_source_rpm_url = ctx_properties['pip_source_rpm_url']
    python_backports_rpm_url = ctx_properties['python_backports_rpm_url']
    python_backports_ssl_match_hostname_rpm_url =\
        ctx_properties['python_backports_ssl_match_hostname_rpm_url']
    python_setuptools_rpm_url = ctx_properties['python_setuptools_rpm_url']

    install_python_compilers = ctx_properties['install_python_compilers']

    ctx.logger.info('Installing Python Requirements...')
    utils.set_selinux_permissive()
    utils.copy_notice('python')

    for rpm in [pip_source_rpm_url,
                python_backports_rpm_url,
                python_backports_ssl_match_hostname_rpm_url,
                python_setuptools_rpm_url]:
        utils.yum_install(rpm, service_name='python')

    if install_python_compilers:
        ctx.logger.info('Installing Compilers...')
        utils.yum_install('python-devel', service_name='python')
        utils.yum_install('gcc', service_name='python')
        utils.yum_install('gcc-c++', service_name='python')


install_python_requirements()

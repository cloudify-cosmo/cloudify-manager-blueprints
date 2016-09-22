#!/usr/bin/env python

from os.path import join, dirname
from cloudify import ctx
ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PS_SERVICE_NAME = 'postgresql-9.5'
ctx_properties = utils.ctx_factory.create(PS_SERVICE_NAME)


def _prepare_env():
    ctx.logger.info('Preparing environment for PostgreSQL installation...')
    utils.set_selinux_permissive()
    postgresql_components_folder = 'postgresql'
    utils.copy_notice(postgresql_components_folder)


def _install_postgresql():
    libxslt_rpm_url = ctx_properties['libxslt_rpm_url']
    ps_rpm_url = ctx_properties['ps_rpm_url']
    ps_contrib_rpm_url = ctx_properties['ps_contrib_rpm_url']
    ps_libs_rpm_url = ctx_properties['ps_libs_rpm_url']
    ps_server_rpm_url = ctx_properties['ps_server_rpm_url']
    ps_devel_rpm_url = ctx_properties['ps_devel_rpm_url']
    psycopg2_rpm_url = ctx_properties['psycopg2_rpm_url']

    ctx.logger.info('Installing PostgreSQL dependencies...')
    utils.yum_install(source=libxslt_rpm_url, service_name=PS_SERVICE_NAME)

    ctx.logger.info('Installing PostgreSQL...')
    utils.yum_install(source=ps_libs_rpm_url, service_name=PS_SERVICE_NAME)
    utils.yum_install(source=ps_rpm_url, service_name=PS_SERVICE_NAME)
    utils.yum_install(source=ps_contrib_rpm_url, service_name=PS_SERVICE_NAME)
    utils.yum_install(source=ps_server_rpm_url, service_name=PS_SERVICE_NAME)
    utils.yum_install(source=ps_devel_rpm_url, service_name=PS_SERVICE_NAME)

    ctx.logger.info('Installing python libs for PostgreSQL...')
    utils.yum_install(source=psycopg2_rpm_url, service_name=PS_SERVICE_NAME)


def _install_stolon():
    utils.yum_install('go', PS_SERVICE_NAME)
    utils.yum_install('git', PS_SERVICE_NAME)

    utils.sudo([
        'git',
        'clone',
        'https://github.com/sorintlab/stolon',
        '/opt/cloudify/stolon'
    ])
    ctx.logger.info('Building stolon')
    utils.sudo(['/opt/cloudify/stolon/build'])


def _prepare_data_dir():
    utils.mkdir(ctx_properties['data_dir'])
    utils.chown(ctx_properties['user'], ctx_properties['user'],
                ctx_properties['data_dir'])


def main():
    _prepare_env()
    _install_postgresql()
    _install_stolon()
    _prepare_data_dir()

main()

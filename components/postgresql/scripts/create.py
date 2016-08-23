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


def _init_postgresql():
    ctx.logger.info('Init PostreSQL DATA folder...')
    postgresql95_setup = '/usr/pgsql-9.5/bin/postgresql95-setup'
    utils.sudo(command=[postgresql95_setup, 'initdb'])

    ctx.logger.info('Starting PostgreSQL server...')
    utils.systemd.enable(service_name=PS_SERVICE_NAME, append_prefix=False)
    utils.systemd.start(service_name=PS_SERVICE_NAME, append_prefix=False)

    ctx.logger.info('Setting PostgreSQL logs path...')
    ps_95_logs_path = "/var/lib/pgsql/9.5/data/pg_log"
    ps_logs_path = "/var/log/cloudify/postgresql"
    utils.mkdir(ps_logs_path)
    utils.ln(source=ps_95_logs_path, target=ps_logs_path, params='-s')


def main():
    _prepare_env()
    _install_postgresql()
    _init_postgresql()
    utils.systemd.restart(service_name=PS_SERVICE_NAME, append_prefix=False)


main()

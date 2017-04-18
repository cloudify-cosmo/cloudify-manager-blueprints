#!/usr/bin/env python

import os
from os.path import join, dirname
from cloudify import ctx
ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'postgresql-9.5'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME
PGSQL_LIB_DIR = '/var/lib/pgsql'
PGSQL_USR_DIR = '/usr/pgsql-9.5'
PGSQL_LOGS_DIR = join(utils.BASE_LOG_DIR, 'postgresql')
runtime_props['files_to_remove'] = [
    PGSQL_LIB_DIR, PGSQL_USR_DIR, PGSQL_LOGS_DIR]

ctx_properties = utils.ctx_factory.create(SERVICE_NAME)


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
    utils.yum_install(source=libxslt_rpm_url, service_name=SERVICE_NAME)

    ctx.logger.info('Installing PostgreSQL...')
    utils.yum_install(source=ps_libs_rpm_url, service_name=SERVICE_NAME)
    utils.yum_install(source=ps_rpm_url, service_name=SERVICE_NAME)
    utils.yum_install(source=ps_contrib_rpm_url, service_name=SERVICE_NAME)
    utils.yum_install(source=ps_server_rpm_url, service_name=SERVICE_NAME)
    utils.yum_install(source=ps_devel_rpm_url, service_name=SERVICE_NAME)

    ctx.logger.info('Installing python libs for PostgreSQL...')
    utils.yum_install(source=psycopg2_rpm_url, service_name=SERVICE_NAME)


def _init_postgresql():
    ctx.logger.info('Initializing PostreSQL DATA folder...')
    postgresql95_setup = join(PGSQL_USR_DIR, 'bin', 'postgresql95-setup')
    try:
        utils.sudo(command=[postgresql95_setup, 'initdb'])
    except Exception:
        ctx.logger.debug('PostreSQL DATA folder already been init...')
        pass

    ctx.logger.info('Starting PostgreSQL server...')
    utils.systemd.enable(service_name=SERVICE_NAME, append_prefix=False)
    utils.systemd.start(service_name=SERVICE_NAME, append_prefix=False)

    ctx.logger.info('Setting PostgreSQL logs path...')
    ps_95_logs_path = join(PGSQL_LIB_DIR, '9.5', 'data', 'pg_log')
    utils.mkdir(PGSQL_LOGS_DIR)
    if not os.path.isdir(ps_95_logs_path):
        utils.ln(source=ps_95_logs_path, target=PGSQL_LOGS_DIR, params='-s')


def main():
    _prepare_env()
    _install_postgresql()
    _init_postgresql()
    utils.systemd.restart(service_name=SERVICE_NAME, append_prefix=False)


main()

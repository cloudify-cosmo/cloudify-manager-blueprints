#!/usr/bin/env python

import os
import tempfile
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PS_SERVICE_NAME = 'postgresql-9.5'
ctx_properties = utils.ctx_factory.get(PS_SERVICE_NAME)


def _start_services():

    for service_name in ['stolon-sentinel', 'stolon-keeper', 'stolon-proxy']:
        ctx.logger.info('Starting {0}...'.format(service_name))
        utils.systemd.enable(service_name)
        utils.start_service(service_name)
        utils.systemd.verify_alive(service_name)


def _create_postgres_pass_file(host, db_name, username, password, port=5432):
    pgpass_path = '/root/.pgpass'
    ctx.logger.info('Creating postgresql pgpass file: {0}'.format(
        pgpass_path))
    pgpass_content = '{host}:{port}:{db_name}:{user}:{password}'.format(
        host=host,
        port=port,
        db_name=db_name,
        user=username,
        password=password
    )
    # .pgpass file used by mgmtworker in snapshot workflow,
    # and need to be under th home directory of the user who run the snapshot
    # (currently root)
    if os.path.isfile(pgpass_path):
        ctx.logger.debug('Deleting {0} file..'.format(
            pgpass_path
        ))
        os.remove(pgpass_path)
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(pgpass_content)
        temp_file.flush()
        utils.chmod('0600', temp_file.name)
        utils.move(source=temp_file.name,
                   destination=pgpass_path,
                   rename_only=True)
        ctx.logger.debug('Postgresql pass file {0} created'.format(
            pgpass_path))


def psql(cmd):
    return utils.sudo([
        'env',
        'PGPASSWORD={0}'.format(ctx_properties['pg_su_password']),
        'psql',
        '--host', '127.0.0.1',
        '--port', '25432',
        '-U', 'postgres',
        '-c', cmd
    ], ignore_failures=True)


def _create_default_db(db_name, username, password):
    # XXX use psycopg2, since we're installing it anyway?
    user_exists = psql(
        "select 'exists' from pg_user where usename='{0}';".format(username)
    )
    if 'exists' not in user_exists.aggr_stdout:
        psql("create user {0} with password '{1}' login createdb;"
             .format(username, password))

    db_exists = psql(
        "select 'exists' from pg_database where datname='{0}';".format(db_name)
    )
    if 'exists' not in db_exists.aggr_stdout:
        psql('create database {0} with owner {1};'.format(db_name, username))


@utils.retry(RuntimeError, tries=20)
def _check_postgresql_up():
    ret = psql('select 1;')
    if ret.returncode != 0:
        raise RuntimeError('pg not running')


def main():
    db_name = ctx.node.properties['postgresql_db_name']
    host = ctx.node.properties['postgresql_host']
    _create_postgres_pass_file(host=host,
                               db_name='*',
                               username='cloudify',
                               password='cloudify',
                               port=25432)
    _start_services()

    # need to wait for the cluster to bootstrap and choose a master
    _check_postgresql_up()
    _create_default_db(db_name=db_name,
                       username='cloudify',
                       password='cloudify')

    if utils.is_upgrade or utils.is_rollback:
        # restore the 'provider_context' and 'snapshot' elements from file
        # created in the 'create.py' script.
        ctx.logger.error('NOT IMPLEMENTED - need to restore upgrade data')


main()

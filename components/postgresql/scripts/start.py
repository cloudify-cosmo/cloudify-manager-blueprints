#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PS_SERVICE_NAME = 'postgresql-9.5'
ctx_properties = utils.ctx_factory.get(PS_SERVICE_NAME)


def _start_postgres():
    ctx.logger.info('Starting PostgreSQL Service...')
    utils.systemd.stop(service_name=PS_SERVICE_NAME,
                       append_prefix=False)
    utils.systemd.start(service_name=PS_SERVICE_NAME,
                        append_prefix=False)
    utils.systemd.verify_alive(service_name=PS_SERVICE_NAME,
                               append_prefix=False)


def _create_default_db(db_name, username, password):
    ctx.logger.info('Creating default postgresql database: {0}...'.format(
        db_name))
    # TODO: join...
    ps_config_dir = 'components/postgresql/config'
    ps_config_source = join(ps_config_dir, 'create_default_db.sh')
    # TODO: Replace with tempfile.gettempdir() and join
    ps_config_destination = '/tmp/create_default_db.sh'
    ctx.download_resource(source=ps_config_source,
                          destination=ps_config_destination)
    # TODO: Use utils.chmod...
    utils.run('chmod +x {0}'.format(ps_config_destination))
    # TODO: Can't we use a rest call here? Is there such a thing?
    utils.run('su - postgres -c "{cmd} {db} {user} {password}"'.format(
        cmd=ps_config_destination,
        db=db_name,
        user=username,
        password=password))


def main():
    db_name = ctx.node.properties['postgresql_db_name']
    _start_postgres()
    _create_default_db(db_name=db_name,
                       username='cloudify',
                       password='cloudify')

    if utils.is_upgrade or utils.is_rollback:
        # restore the 'provider_context' and 'snapshot' elements from file
        # created in the 'create.py' script.
        ctx.logger.error('NOT IMPLEMENTED - need to restore upgrade data')


main()

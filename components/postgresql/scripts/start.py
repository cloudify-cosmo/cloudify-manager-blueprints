#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PS_SERVICE_NAME = 'postgresql-9.5'
ctx_properties = utils.ctx_factory.get(PS_SERVICE_NAME)


def main():
    ctx.logger.info('Starting PostgreSQL Service...')
    utils.start_service(PS_SERVICE_NAME, append_prefix=False)
    utils.systemd.verify_alive(PS_SERVICE_NAME, append_prefix=False)

    if utils.is_upgrade or utils.is_rollback:
        # restore the 'provider_context' and 'snapshot' elements from file
        # created in the 'create.py' script.
        ctx.logger.error('NOT IMPLEMENTED - need to restore upgrade data')

main()

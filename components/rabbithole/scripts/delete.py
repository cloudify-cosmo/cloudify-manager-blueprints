#!/usr/bin/env python

from cloudify import ctx

import utils  # noqa

SERVICE_NAME = 'rabbithole'

if __name__ == '__main__':
    ctx.logger.info('Deleting rabbithole...')
    ctx.logger.info('Deleting virtualenv...')
    utils.remove('/opt/{}'.format(SERVICE_NAME))
    ctx.logger.info('Deleting configuration...')
    utils.remove('/etc/opt/{}'.format(SERVICE_NAME))
    ctx.logger.info('Deleting service file...')
    utils.remove('/etc/systemd/system/{}'.format(SERVICE_NAME))

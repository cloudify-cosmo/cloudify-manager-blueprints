#!/usr/bin/env python

from cloudify import ctx

import subprocess

SERVICE_NAME = 'rabbithole'

if __name__ == '__main__':
    ctx.logger.info('Stopping rabbithole...')
    subprocess.Popen(['systemctl', 'stop', SERVICE_NAME])

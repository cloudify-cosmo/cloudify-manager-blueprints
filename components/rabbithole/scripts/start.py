#!/usr/bin/env python

from cloudify import ctx

import subprocess

SERVICE_NAME = 'rabbithole'

if __name__ == '__main__':
    ctx.logger.info('Starting rabbithole...')
    subprocess.Popen(['systemctl', 'start', SERVICE_NAME])

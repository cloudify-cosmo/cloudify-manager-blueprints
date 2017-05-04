#!/usr/bin/env python

"""Install rabbithole in a virtualenv."""

import os

from cloudify import ctx

import utils  # noqa

SERVICE_NAME = 'rabbithole'


def main():
    """Install rabbithole in a virtualenv."""
    ctx.logger.info('Creating {} virtualenv...'.format(SERVICE_NAME))
    venv_dir = os.path.join('/opt', SERVICE_NAME, 'env')

    utils.run(['pip', 'install', 'virtualenv'])
    utils.run(['virtualenv', venv_dir])

    ctx.logger.info('Pip installing rabbithole...')
    utils.install_python_package(
        'rabbithole[postgresql]==0.3',
        venv=venv_dir,
    )


if __name__ == '__main__':
    main()

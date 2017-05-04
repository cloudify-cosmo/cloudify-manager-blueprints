#!/usr/bin/env python

"""Configure rabbithole."""

import os

from cloudify import ctx

import utils  # noqa

SERVICE_NAME = 'rabbithole'
SERVICE_PATH = '/etc/systemd/system'
SERVICE_FILENAME = '{}.service'.format(SERVICE_NAME)
VIRTUALENV_PATH = '/opt/{}/env'.format(SERVICE_NAME)
CONFIG_PATH = '/etc/opt/{}'.format(SERVICE_NAME)
CONFIG_FILENAME = 'config.yml'
LOG_FILENAME = '/var/log/cloudify/{}.log'.format(SERVICE_NAME)
SERVICE_FILE_CONTENT = """
[Unit]
Description=rabbithole

[Service]
ExecStart={}/bin/rabbithole -l debug -f {} {}/{}
""".format(VIRTUALENV_PATH, LOG_FILENAME, CONFIG_PATH, CONFIG_FILENAME)


def main():
    """Configure rabbithole."""
    ctx.logger.info('Configuring rabbithole...')
    get_configuration_file()
    generate_systemd_service_file()


def get_configuration_file():
    """Get configuration file from resources."""
    ctx.logger.info('Getting configuration file...')
    utils.mkdir(CONFIG_PATH)
    ctx.download_resource_and_render(
        os.path.join('components', SERVICE_NAME, 'config', CONFIG_FILENAME),
        os.path.join(CONFIG_PATH, CONFIG_FILENAME),
    )


def generate_systemd_service_file():
    """Generate systemd service file to start/stop rabbithole."""
    ctx.logger.info('Generating systemd service file...')
    service_filename = os.path.join(SERVICE_PATH, SERVICE_FILENAME)
    with open(service_filename, 'w') as service_file:
        service_file.write(SERVICE_FILE_CONTENT)


if __name__ == '__main__':
    main()

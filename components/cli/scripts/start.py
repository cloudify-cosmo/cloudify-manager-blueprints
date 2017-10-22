from cloudify import ctx

from os.path import join, dirname
ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties


def configure():
    ctx.logger.info('Configuring Cloudify CLI...')

    security_config = runtime_props['security_configuration']
    username = security_config['admin_username']
    password = security_config['admin_password']

    cmd = [
        'cfy', 'profiles', 'use', 'localhost', '-u', username,
        '-p', password, '-t', 'default_tenant'
    ]
    ctx.logger.info('Setting CLI for default user...')
    utils.run(cmd)

    ctx.logger.info('Setting CLI for root user...')
    root_cmd = ['sudo', '-u', 'root'] + cmd
    utils.run(root_cmd)

    ctx.logger.info('Cloudify CLI successfully configured')


configure()

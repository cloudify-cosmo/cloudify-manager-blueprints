#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

SERVICE_NAME = 'cli'
CONFIG_PATH = 'components/{0}/scripts'.format(SERVICE_NAME)

ctx_properties = ctx.node.properties.get_all()


def install():
    ctx.logger.info('Installing Cloudify CLI...')
    source_url = ctx_properties['cli_rpm_source_url']
    cli_source_url = ctx_properties.get('cli_rpm_source_url')
    ctx.logger.info('source_url={0}'.format(source_url))
    ctx.logger.info('cli_source_url={0}'.format(cli_source_url))
    utils.yum_install(source_url,
                      service_name=SERVICE_NAME)
    ctx.logger.info('Cloudify CLI successfully installed')


def copy_start_script():
    try:
        script_name = 'start.sh'
        script_destination = join(utils.get_exec_tempdir(), script_name)
        ctx.download_resource(join(CONFIG_PATH, script_name),
                              script_destination)
        utils.sudo(['mv', script_destination,
                    join(utils.CLOUDIFY_HOME_DIR, script_name)])
    except Exception as ex:
        ctx.logger.info('Failed to deploy copy script. Error: {0}'
                        ''.format(ex))


install()
copy_start_script()

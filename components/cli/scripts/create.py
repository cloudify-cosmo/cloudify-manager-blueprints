#!/usr/bin/env python
import json
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties

SERVICE_NAME = 'cli'
CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)

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
        with open('/opt/manager/rest-security.conf') as security_config_file:
            security_config_content = security_config_file.read()
            security_config = json.loads(security_config_content)
        params = {
            'username': security_config['admin_username'],
            'password': security_config['admin_password']
        }
        script_name = 'config_local_cfy.sh'
        script_destination = join(utils.get_exec_tempdir(), script_name)
        ctx.download_resource_and_render(join(CONFIG_PATH, script_name),
                                         script_destination,
                                         params)
        utils.sudo(['mv', script_destination,
                    join(utils.CLOUDIFY_HOME_DIR, script_name)])
        utils.chmod('+x', join(utils.CLOUDIFY_HOME_DIR, script_name))
    except Exception as ex:
        ctx.logger.warn('Failed to deploy local cli config script. '
                        'Error: {0}'.format(ex))


install()
copy_start_script()

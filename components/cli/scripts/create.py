import os

from cloudify import ctx

ctx.download_resource(os.path.join('components', 'utils.py'), os.path.join(os.path.dirname(__file__), 'utils.py'))  # NOQA
import utils  # NOQA

ctx_properties = ctx.node.properties.get_all()


def install():
    ctx.logger.info('Installing Cloudify CLI...')
    source_url = ctx_properties['cli_rpm_source_url']
    cli_source_url = ctx_properties.get('cli_rpm_source_url')
    ctx.logger.info('source_url={0}'.format(source_url))
    ctx.logger.info('cli_source_url={0}'.format(cli_source_url))
    utils.yum_install(source_url)
    ctx.logger.info('Cloudify CLI successfully installed')


install()

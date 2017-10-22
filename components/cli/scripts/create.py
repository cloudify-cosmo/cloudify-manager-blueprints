from utils.install import yum_install

from cloudify import ctx

from os.path import join, dirname
ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

ctx_properties = ctx.node.properties.get_all()


def install():
    ctx.logger.info('Installing Cloudify CLI...')
    source_url = ctx_properties['cli_rpm_url']
    yum_install(source_url)
    ctx.logger.info('Cloudify CLI successfully installed')


install()

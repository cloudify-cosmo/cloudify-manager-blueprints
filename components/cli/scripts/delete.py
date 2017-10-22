from utils.install import yum_remove

from cloudify import ctx

from os.path import join, dirname
ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


def remove():
    ctx.logger.info('Removing Cloudify CLI...')
    yum_remove('cloudify')
    ctx.logger.info('Cloudify CLI successfully removed  ')


remove()

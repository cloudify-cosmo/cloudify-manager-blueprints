#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


def remove():
    ctx.logger.info('Removing Cloudify CLI...')
    utils.yum_remove('cloudify')
    ctx.logger.info('Cloudify CLI successfully removed  ')


remove()

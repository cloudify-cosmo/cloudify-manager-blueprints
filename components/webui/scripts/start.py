#!/usr/bin/env python

from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


ctx.logger.info('Starting WebUI Service...')
utils.systemd.start('cloudify-webui')

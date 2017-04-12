#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
        join('components', 'utils.py'),
        join(dirname(__file__), 'utils.py'))
import utils  # NOQA

STAGE_SERVICE_NAME = 'stage'

skip_stage_installation = ctx.instance.runtime_properties['skip_stage_installation']
print "skip_stage_installation={0}".format(skip_stage_installation)
if skip_stage_installation != 'True':
    ctx.logger.info('Starting Stage (UI) Service...')
    utils.start_service(STAGE_SERVICE_NAME)

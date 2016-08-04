#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA
PS_SERVICE_NAME = 'postgresql-9.5'

ctx_properties = utils.CtxPropertyFactory().get(PS_SERVICE_NAME)

utils.systemd.stop(PS_SERVICE_NAME, append_prefix=False)

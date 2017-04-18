#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties


if utils.is_upgrade:
    SERVICE_NAME = runtime_props['service_name']
    utils.validate_upgrade_directories(SERVICE_NAME)
    utils.systemd.verify_alive(SERVICE_NAME)

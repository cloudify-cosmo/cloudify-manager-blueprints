#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties


# This makes sure that the `create` script already ran
if runtime_props.get('service_name'):
    utils.remove_component(runtime_props)

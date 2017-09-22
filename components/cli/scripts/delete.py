#!/usr/bin/env python

import os

from cloudify import ctx

if not ctx.node.properties['skip']:
    ctx.download_resource(
        os.path.join('components', 'utils.py'),
        os.path.join(os.path.dirname(__file__), 'utils.py'))
    import utils  # NOQA

    runtime_props = ctx.instance.runtime_properties

    # This makes sure that the `create` script already ran
    if runtime_props.get('service_name'):
        runtime_props['packages_to_remove'] = ['cloudify']

        utils.remove_component(runtime_props)

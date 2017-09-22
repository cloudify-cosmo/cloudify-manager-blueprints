#!/usr/bin/env python

import os

from cloudify import ctx

if not ctx.source.node.properties['skip']:
    ctx.download_resource(
        os.path.join('components', 'utils.py'),
        os.path.join(os.path.dirname(__file__), 'utils.py'))
    import utils  # NOQA

    # Copy admin username/password from the REST service
    # node instance.
    for prop in ['admin_username', 'admin_password']:
        ctx.source.instance.runtime_properties[prop] = \
            ctx.target.instance.runtime_properties['security_configuration'][prop]

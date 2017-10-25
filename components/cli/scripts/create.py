#!/usr/bin/env python

import os

from cloudify import ctx

if not ctx.node.properties['skip']:
    ctx.download_resource(
        os.path.join('components', 'utils.py'),
        os.path.join(os.path.dirname(__file__), 'utils.py'))
    import utils  # NOQA

    SERVICE_NAME = 'cli'

    runtime_props = ctx.instance.runtime_properties
    runtime_props['service_name'] = SERVICE_NAME

    ctx_properties = ctx.node.properties.get_all()

    cli_rpm = ctx_properties['cli_source_url']

    ctx.logger.info('Installing CLI...')
    utils.yum_install(source=cli_rpm, service_name=SERVICE_NAME)

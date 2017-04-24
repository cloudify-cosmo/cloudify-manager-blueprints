#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties
SERVICE_NAME = runtime_props.get('service_name')


# This makes sure that the `create` script already ran
if SERVICE_NAME:
    utils.extend_runtime_properties_list(
        runtime_props,
        'files_to_remove',
        [
            join('/etc', SERVICE_NAME),
            join('/var/log', SERVICE_NAME),
            join('/var/cache', SERVICE_NAME)
        ]
    )
    runtime_props['packages_to_remove'] = [SERVICE_NAME]
    runtime_props['service_user'] = 'nginx'
    runtime_props['service_group'] = 'nginx'
    utils.remove_component(runtime_props)

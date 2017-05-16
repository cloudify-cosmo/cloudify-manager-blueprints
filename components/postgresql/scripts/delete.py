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
    utils.delete_cluster_component('postgresql')

    runtime_props['packages_to_remove'] = ['postgresql95', 'postgresql95-libs']
    runtime_props['service_user'] = 'postgres'
    runtime_props['service_group'] = 'postgres'

    utils.remove_component(runtime_props)
    # Remove the notice manually, as the name differs from the service name
    utils.remove_notice('postgresql')

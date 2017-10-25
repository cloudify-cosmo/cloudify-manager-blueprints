#!/usr/bin/env python

import os

from cloudify import ctx

if not ctx.source.node.properties['skip']:
    ctx.download_resource(
        os.path.join('components', 'utils.py'),
        os.path.join(os.path.dirname(__file__), 'utils.py'))
    import utils  # NOQA

    source_runtime_props = ctx.source.instance.runtime_properties
    target_runtime_props = ctx.target.instance.runtime_properties

    rest_host = 'localhost'
    rest_port = target_runtime_props['internal_rest_port']
    username = source_runtime_props['admin_username']
    password = source_runtime_props['admin_password']
    cert_path = utils.INTERNAL_CERT_PATH

    utils.run(['cfy', 'profiles', 'use', rest_host, '--rest-port', rest_port,
               '-u', username, '-p', password, '-t', 'default_tenant',
               '-c', cert_path])

    ctx.logger.info('CLI profile created on manager')

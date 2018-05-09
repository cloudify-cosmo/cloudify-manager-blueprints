#!/usr/bin/env python

from cloudify import ctx


def get_rest_config():
    target_runtime_properties = ctx.target.instance.runtime_properties
    rest_protocol = 'https'
    rest_port = target_runtime_properties['internal_rest_port']

    ctx.source.instance.runtime_properties['rest_protocol'] = rest_protocol
    ctx.source.instance.runtime_properties['rest_port'] = rest_port

    ctx.source.instance.runtime_properties['security_configuration'] = \
        ctx.target.node.properties['security']


get_rest_config()

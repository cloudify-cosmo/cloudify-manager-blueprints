#!/usr/bin/env python

from cloudify import ctx


def get_rest_config():
    target_runtime_properties = ctx.target.instance.runtime_properties
    rest_protocol = target_runtime_properties['external_rest_protocol']
    rest_port = target_runtime_properties['external_rest_port']

    ctx.source.instance.runtime_properties['rest_protocol'] = rest_protocol
    ctx.source.instance.runtime_properties['rest_port'] = rest_port


get_rest_config()

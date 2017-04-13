#!/usr/bin/env python

from cloudify import ctx


def preconfigure_restservice():
    security_config = ctx.target.node.properties['security']
    ctx.source.instance.runtime_properties['security_configuration'] = \
        security_config
    ctx.source.instance.runtime_properties['file_server_url'] = \
        ctx.target.instance.runtime_properties['file_server_url']


preconfigure_restservice()

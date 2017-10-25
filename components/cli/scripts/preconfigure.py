#!/usr/bin/env python

from cloudify import ctx


def preconfigure_restservice():
    security_config = ctx.target.node.properties['security']
    ctx.source.instance.runtime_properties['security_configuration'] = \
        security_config


preconfigure_restservice()

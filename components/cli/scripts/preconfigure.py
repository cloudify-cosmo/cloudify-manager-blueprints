#!/usr/bin/env python

from cloudify import ctx


def preconfigure_restservice():
    security_config = ctx.target.node.properties['security']
    ctx.source.instance.runtime_properties['security_configuration'] = \
        security_config
    # ctx.source.instance.runtime_properties['admin_username'] = security_config['admin_username']
    # ctx.source.instance.runtime_properties['admin_password'] = security_config['admin_password']


preconfigure_restservice()
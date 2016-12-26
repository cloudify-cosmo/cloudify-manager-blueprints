#!/usr/bin/env python

from cloudify import ctx


def preconfigure_restservice():
    ctx.logger.info('Setting up security configuration...')
    security_config = ctx.target.node.properties['security']
    ctx.logger.debug('Security_config is: {0}'.format(security_config))
    ctx.source.instance.runtime_properties['security_configuration'] = \
        security_config


preconfigure_restservice()

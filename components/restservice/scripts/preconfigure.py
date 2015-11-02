#!/usr/bin/env python

from cloudify import ctx


def preconfigure_restservice():

    ctx.logger.info('Reading security property from manager_configuration...')
    security_config = ctx.target.node.properties['security']
    ctx.logger.info('security_config is: {0}'.format(security_config))
    ctx.source.instance.runtime_properties['security_configuration'] = \
        security_config

preconfigure_restservice()

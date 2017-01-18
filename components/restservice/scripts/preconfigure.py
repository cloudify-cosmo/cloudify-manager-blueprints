#!/usr/bin/env python

import json
from cloudify import ctx


def preconfigure_restservice():
    ctx.logger.info('Setting up security configuration...')
    security_config = ctx.target.node.properties['security']
    ctx.logger.debug('Security config is: {0}'.format(security_config))
    ctx.source.instance.runtime_properties['security_configuration'] = \
        json.dumps(security_config)


preconfigure_restservice()

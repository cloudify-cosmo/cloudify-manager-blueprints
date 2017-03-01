#!/usr/bin/env python

import json
from cloudify import ctx


def preconfigure_restservice():
    security_config = ctx.target.node.properties['security']
    ctx.source.instance.runtime_properties['security_configuration'] = \
        json.dumps(security_config)
    ctx.source.instance.runtime_properties['file_server_url'] = \
        ctx.target.instance.runtime_properties['file_server_url']


preconfigure_restservice()

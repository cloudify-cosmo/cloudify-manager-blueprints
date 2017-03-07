#!/usr/bin/env python

from cloudify import ctx


def main():
    """Get rabbitmq configuration needed to generate logstash.conf file."""
    source = ctx.source.instance.runtime_properties
    target = ctx.target.node.properties
    props = [
        'rabbitmq_username',
        'rabbitmq_password',
    ]
    for prop in props:
        source[prop] = target[prop]


if __name__ == '__main__':
    main()

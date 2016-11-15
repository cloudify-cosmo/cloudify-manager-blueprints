#!/usr/bin/env python

from cloudify import ctx


def main():
    """Get postgresql configuration needed to generate logstash.conf file."""
    source = ctx.source.instance.runtime_properties
    target = ctx.target.node.properties
    props = [
        'postgresql_host',
        'postgresql_db_name',
        'postgresql_username',
        'postgresql_password',
    ]
    for prop in props:
        source[prop] = target[prop]


if __name__ == '__main__':
    main()

#!/usr/bin/env python

from cloudify import ctx


def main():
    """Get elasticsearch configuration needed to generate logstash.conf."""
    target = ctx.target
    source = ctx.source.instance.runtime_properties
    source['es_endpoint_ip'] = (
        target.instance.runtime_properties['es_endpoint_ip']
    )
    source['es_endpoint_port'] = target.node.properties['es_endpoint_port']


if __name__ == '__main__':
    main()

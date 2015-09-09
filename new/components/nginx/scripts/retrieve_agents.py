#!/bin/python


from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
import platform
import os
import fabric.api


def _get_distro_info():
    distro, _, release = platform.linux_distribution(
        full_distribution_name=False)
    return '{0} {1}'.format(distro, release)


def retrieve(agent_packages):
    ctx.logger.info('Downloading Cloudify Agents...')
    if not agent_packages:
        raise NonRecoverableError(
            'Cannot find agent packages. At least one agent package must be '
            'provided compatible with {0}.'.format(_get_distro_info))

    for agent, source_url in agent_packages.items():
        dest_path = ctx.instance.runtime_properties['agent_packages_path']
        agent_name = agent.replace('_', '-')
        if agent_name == 'cloudify-windows-agent':
            filename = '{0}.exe'.format(agent_name)
        else:
            filename = '{0}.tar.gz'.format(agent_name)
        dest_file = os.path.join(dest_path, filename)
        dl_cmd = 'curl --retry 10 -f -s -S -L {0} --create-dirs -o {1}'.format(
            source_url, dest_file)

        ctx.logger.info('Downloading Agent Package {0} to {1}...'.format(
            source_url, dest_file))
        fabric.api.sudo(dl_cmd)

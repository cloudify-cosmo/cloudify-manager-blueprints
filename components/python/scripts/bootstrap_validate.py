#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


# Most images already ship with the following packages:
#
#   python-setuptools
#   python-backports
#   python-backports-ssl_match_hostname
#
# - as they are dependencies of cloud-init, which is extremely popular.
#
# However, cloud-init is irrelevant for certain IaaS (such as vSphere) so
# images used there may not have these packages preinstalled.
#
# We're currently considering whether to include these libraries in the
# manager resources package. Until then, we only validate that they're
# preinstalled, and if not - instruct the user to install them.

missing_packages = set()

for pkg in ['python-setuptools',
            'python-backports',
            'python-backports-ssl_match_hostname']:
    ctx.logger.info('Ensuring {0} is installed'.format(pkg))
    is_installed = utils.RpmPackageHandler.is_package_installed(pkg)
    if not is_installed:
        missing_packages.add(pkg)

if missing_packages:
    ctx.abort_operation('Prerequisite packages missing: {0}. '
                        'Please ensure these packages are installed and '
                        'try again'.format(', '.join(missing_packages)))

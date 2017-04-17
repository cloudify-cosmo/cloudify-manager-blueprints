
# This script has to run using the Python executable found in:
# /opt/cfy/embedded/bin/python in order to properly load the manager
# blueprints utils.py module.

import logging
import sys

import utils


class CtxWithLogger(object):
    logger = logging.getLogger('internal-ssl-certs-logger')


utils.ctx = CtxWithLogger()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Expected 1 argument - <manager-ip>')
        print('Provided args: {0}'.format(sys.argv[1:]))
        sys.exit(1)
    utils.generate_internal_ssl_cert(sys.argv[1])

#!/opt/manager/env/bin/python

import imp
import logging
import sys


UTILS_MODULE_PATH = '/opt/cfy/cloudify-manager-blueprints/components/utils.py'


class CtxWithLogger(object):
    logger = logging.getLogger('internal-ssl-certs-logger')


utils = imp.load_source('utils', UTILS_MODULE_PATH)
utils.ctx = CtxWithLogger()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Expected 1 argument - <manager-ip>')
        print('Provided args: {0}'.format(sys.argv[1:]))
        sys.exit(1)
    utils.generate_internal_ssl_cert(sys.argv[1])

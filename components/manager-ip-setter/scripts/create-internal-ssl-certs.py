# This script has to run using the Python executable found in:
# /opt/mgmtworker/env/bin/python in order to properly load the manager
# blueprints utils.py module.

import argparse
import logging

import utils


class CtxWithLogger(object):
    logger = logging.getLogger('internal-ssl-certs-logger')


utils.ctx = CtxWithLogger()

parser = argparse.ArgumentParser()
parser.add_argument('--metadata', default=utils.CERT_METADATA_FILE_PATH,
                    help='File containing the cert metadata. It should be a '
                         'JSON file containing an object with the '
                         '"internal_rest_host" and "networks" fields.')
parser.add_argument('manager_ip', default=None, nargs='?',
                    help='The IP of this machine on the default network')

if __name__ == '__main__':
    args = parser.parse_args()
    cert_metadata = utils.load_cert_metadata(filename=args.metadata)
    internal_rest_host = args.manager_ip or cert_metadata['internal_rest_host']

    networks = cert_metadata.get('networks', {})
    networks['default'] = internal_rest_host
    cert_ips = [internal_rest_host] + list(networks.values())
    utils.generate_internal_ssl_cert(ips=cert_ips, name=internal_rest_host)
    utils.store_cert_metadata(internal_rest_host, networks,
                              filename=args.metadata)

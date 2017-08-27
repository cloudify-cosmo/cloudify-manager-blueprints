import os
import sys
from unittest import TestCase

sys.path.append(os.path.join(os.path.dirname(__file__),
                             '../../components'))
import utils  # NOQA


class CertMetadataTest(TestCase):
    def test_none_and_empty(self):
        with self.assertRaises(AssertionError):
            utils._get_cert_ips_and_dns(None, None)
        with self.assertRaises(AssertionError):
            utils._get_cert_ips_and_dns([], None)

    def test_single(self):
        ips, dns = utils._get_cert_ips_and_dns(['10.0.0.1'])
        self.assertSetEqual(ips, {'10.0.0.1', '127.0.0.1'})
        self.assertSetEqual(dns, {'localhost', '10.0.0.1', '127.0.0.1'})

    def test_both(self):
        ips, dns = utils._get_cert_ips_and_dns(['10.0.0.1'],
                                               ['www.cloudify.co',
                                                'localhost'])
        self.assertSetEqual(ips, {'10.0.0.1', '127.0.0.1'})
        self.assertSetEqual(dns, {'localhost', '10.0.0.1', '127.0.0.1',
                                  'www.cloudify.co'})

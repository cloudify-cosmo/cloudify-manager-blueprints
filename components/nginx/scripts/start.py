#!/usr/bin/env python

import subprocess
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties
SERVICE_NAME = runtime_props['service_name']


def verify_nginx(url):
    """Check if the response looks like a correct REST service response.

    We can get a 200, or a 401 in case auth is enabled. We don't expect a
    502, though, as this would mean nginx isn't correctly proxying to
    the REST service.
    """
    # We can't easily use python's urllib here, because we would need
    # to keep compatibility between python versions that do https
    # cert verification (2.7.9+, and 2.7.5 with centos patches starting from
    # 2.7.5-58), and ones that don't.
    # Instead, we use curl, because it behaves consistently across distro
    # versions.
    # See also CFY-7222
    try:
        output = subprocess.check_output([
            'curl',
            url,
            '--cacert', utils.INTERNAL_CA_CERT_PATH,
            # only output the http code
            '-o', '/dev/null',
            '-w', '%{http_code}'
        ])
    except subprocess.CalledProcessError:
        ctx.abort_operation('Nginx HTTP check error')
    if output.strip() not in {'200', '401'}:
        ctx.abort_operation('Nginx HTTP check error: {0}'.format(output))


utils.start_service(SERVICE_NAME, append_prefix=False)
utils.systemd.verify_alive(SERVICE_NAME, append_prefix=False)

nginx_url = 'https://127.0.0.1:{0}/api/v2.1/version'.format(
    runtime_props['internal_rest_port'])
verify_nginx(nginx_url)

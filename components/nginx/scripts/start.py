#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties
SERVICE_NAME = runtime_props['service_name']


def check_response(response):
    """Check if the response looks like a correct REST service response.

    We can get a 200, or a 401 in case auth is enabled. We don't expect a
    502, though, as this would mean nginx isn't correctly proxying to
    the REST service.
    """
    return response.code in {200, 401}


utils.start_service(SERVICE_NAME, append_prefix=False)
utils.systemd.verify_alive(SERVICE_NAME, append_prefix=False)

nginx_url = '{0}://127.0.0.1/api/v2.1/version'.format(
    runtime_props['external_rest_protocol'])

headers = {}
if utils.is_upgrade or utils.is_rollback:
    headers = utils.create_maintenance_headers()

utils.verify_service_http(
    SERVICE_NAME,
    nginx_url,
    check_response,
    headers=headers
)

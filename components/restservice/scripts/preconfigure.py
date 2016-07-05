#!/usr/bin/env python

import os
import json
import binascii
import tempfile
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

REST_SERVICE_NAME = 'restservice'

TOKEN_AUTHENTICATOR = \
    'flask_securest.authentication_providers.token:TokenAuthenticator'


def add_transient_security_properties(settings):
    """Add security-related properties that should change for each manager.

    Some values (like the token generator secret key) should be different
    for each manager, because reusing them would be a security issue.
    Examine the security config, generate the required values and add
    them to settings.
    """
    secret_key = binascii.hexlify(os.urandom(32))
    for auth_provider in settings.get('authentication_providers', []):
        if auth_provider.get('implementation') == TOKEN_AUTHENTICATOR:
            if 'properties' not in auth_provider:
                auth_provider['properties'] = {}
            auth_provider['properties']['secret_key'] = secret_key

    auth_token_generator = settings.get('auth_token_generator')
    if auth_token_generator and auth_token_generator.get('implementation') \
            == TOKEN_AUTHENTICATOR:
        if 'properties' not in auth_token_generator:
            auth_token_generator['properties'] = {}
        auth_token_generator['properties']['secret_key'] = secret_key


def preconfigure_restservice():

    rest_service_home = '/opt/manager'

    ctx.logger.info('Deploying REST Security configuration file...')
    sec_config = json.loads(utils.load_manager_config_prop('security'))
    add_transient_security_properties(sec_config)

    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        json.dump(sec_config, f)
    utils.move(path, os.path.join(rest_service_home, 'rest-security.conf'))

    utils.systemd.configure(REST_SERVICE_NAME, render=False)


preconfigure_restservice()

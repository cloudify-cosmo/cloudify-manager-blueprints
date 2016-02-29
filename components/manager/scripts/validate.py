import os

from cloudify import ctx
from cloudify_cli import constants
from cloudify.exceptions import NonRecoverableError

security_enabled = ctx.node.properties.get('security', {}).get('enabled', False)

if security_enabled:
    missing_keys = {constants.CLOUDIFY_USERNAME_ENV,
                    constants.CLOUDIFY_PASSWORD_ENV} -\
                   set(os.environ.keys())

    if missing_keys:
        raise NonRecoverableError(
            'Security is enabled, but the following required environment '
            'variables have not been set: {0}'.format(", ".join(missing_keys)))

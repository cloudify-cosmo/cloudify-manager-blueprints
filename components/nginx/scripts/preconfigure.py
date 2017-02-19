#!/usr/bin/env python
# source: nginx -> target: manager_configuration

from os.path import join, dirname
from collections import namedtuple

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

NGINX_CONF_PATH = 'components/nginx/config'


def _deploy_nginx_config_files(external_rest_protocol, file_server_protocol):
    resource = namedtuple('Resource', 'src dst')
    ctx.logger.info('Deploying Nginx configuration files...')

    resources = [
        resource(
            src='{0}/{1}-external-rest-server.cloudify'.format(
                NGINX_CONF_PATH,
                external_rest_protocol
            ),
            dst='/etc/nginx/conf.d/{0}-external-rest-server.cloudify'.format(
                external_rest_protocol
            )
        ),
        resource(
            src='{0}/https-internal-rest-server.cloudify'.format(
                NGINX_CONF_PATH
            ),
            dst='/etc/nginx/conf.d/https-internal-rest-server.cloudify'
        ),
        resource(
            src='{0}/{1}-file-server.cloudify'.format(
                NGINX_CONF_PATH,
                file_server_protocol
            ),
            dst='/etc/nginx/conf.d/{0}-file-server.cloudify'.format(
                file_server_protocol
            )
        ),
        resource(
            src='{0}/nginx.conf'.format(NGINX_CONF_PATH),
            dst='/etc/nginx/nginx.conf'
        ),
        resource(
            src='{0}/default.conf'.format(NGINX_CONF_PATH),
            dst='/etc/nginx/conf.d/default.conf',
        ),
        resource(
            src='{0}/rest-location.cloudify'.format(NGINX_CONF_PATH),
            dst='/etc/nginx/conf.d/rest-location.cloudify',
        ),
        resource(
            src='{0}/fileserver-location.cloudify'.format(NGINX_CONF_PATH),
            dst='/etc/nginx/conf.d/fileserver-location.cloudify',
        ),
        resource(
            src='{0}/redirect-to-fileserver.cloudify'.format(NGINX_CONF_PATH),
            dst='/etc/nginx/conf.d/redirect-to-fileserver.cloudify',
        ),
        resource(
            src='{0}/ui-locations.cloudify'.format(NGINX_CONF_PATH),
            dst='/etc/nginx/conf.d/ui-locations.cloudify',
        ),
        resource(
            src='{0}/logs-conf.cloudify'.format(NGINX_CONF_PATH),
            dst='/etc/nginx/conf.d/logs-conf.cloudify',
        )
    ]

    for resource in resources:
        utils.deploy_blueprint_resource(
            resource.src,
            resource.dst,
            utils.NGINX_SERVICE_NAME,
            load_ctx=False
        )


def preconfigure_nginx():

    target_runtime_props = ctx.target.instance.runtime_properties
    src_runtime_props = ctx.source.instance.runtime_properties

    # This is used by nginx's default.conf to select the relevant configuration
    external_rest_protocol = target_runtime_props['external_rest_protocol']
    file_server_protocol = target_runtime_props['file_server_protocol']
    internal_cert_path, internal_key_path = utils.generate_internal_ssl_cert(
        target_runtime_props['internal_rest_host']
    )

    src_runtime_props['external_rest_protocol'] = external_rest_protocol
    src_runtime_props['file_server_protocol'] = file_server_protocol
    src_runtime_props['internal_cert_path'] = internal_cert_path
    src_runtime_props['internal_key_path'] = internal_key_path

    # Pass on the the path to the certificate to manager_configuration
    target_runtime_props['internal_cert_path'] = internal_cert_path

    if external_rest_protocol == 'https':
        external_cert_path, external_key_path = \
            utils.deploy_or_generate_external_ssl_cert(
                target_runtime_props['external_rest_host']
            )

        src_runtime_props['external_cert_path'] = external_cert_path
        src_runtime_props['external_key_path '] = external_key_path

        # The public cert content is used in the outputs later
        external_rest_cert_content = utils.get_file_content(external_cert_path)
        target_runtime_props['external_rest_cert_content'] = \
            external_rest_cert_content

    _deploy_nginx_config_files(external_rest_protocol, file_server_protocol)
    utils.systemd.enable(utils.NGINX_SERVICE_NAME, append_prefix=False)


preconfigure_nginx()

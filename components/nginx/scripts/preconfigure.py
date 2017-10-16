#!/usr/bin/env python
# source: nginx -> target: manager_configuration

from os.path import join, dirname
from collections import namedtuple

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

src_runtime_props = ctx.source.instance.runtime_properties
NGINX_SERVICE_NAME = src_runtime_props['service_name']
CONFIG_PATH = 'components/{0}/config'.format(NGINX_SERVICE_NAME)


def _deploy_nginx_config_files():
    resource = namedtuple('Resource', 'src dst')
    ctx.logger.info('Deploying Nginx configuration files...')

    resources = [
        resource(
            src='{0}/http-external-rest-server.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/http-external-rest-server.cloudify'
        ),
        resource(
            src='{0}/https-external-rest-server.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/https-external-rest-server.cloudify'
        ),
        resource(
            src='{0}/https-internal-rest-server.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/https-internal-rest-server.cloudify'
        ),
        resource(
            src='{0}/https-file-server.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/https-file-server.cloudify'
        ),
        resource(
            src='{0}/nginx.conf'.format(CONFIG_PATH),
            dst='/etc/nginx/nginx.conf'
        ),
        resource(
            src='{0}/default.conf'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/default.conf',
        ),
        resource(
            src='{0}/rest-location.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/rest-location.cloudify',
        ),
        resource(
            src='{0}/fileserver-location.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/fileserver-location.cloudify',
        ),
        resource(
            src='{0}/redirect-to-fileserver.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/redirect-to-fileserver.cloudify',
        ),
        resource(
            src='{0}/ui-locations.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/ui-locations.cloudify',
        ),
        resource(
            src='{0}/composer-location.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/composer-location.cloudify',
        ),
        resource(
            src='{0}/logs-conf.cloudify'.format(CONFIG_PATH),
            dst='/etc/nginx/conf.d/logs-conf.cloudify',
        )
    ]

    for resource in resources:
        utils.deploy_blueprint_resource(
            resource.src,
            resource.dst,
            NGINX_SERVICE_NAME,
            load_ctx=False
        )


def _deploy_cert_and_key(cert_src, key_src, cert_path, key_path):
    def _try_deploy(src, dest):
        try:
            utils.deploy_blueprint_resource(
                src_runtime_props[src], dest, NGINX_SERVICE_NAME,
                user_resource=True, load_ctx=False)
            return True
        except Exception as e:
            if "No such file or directory" in e.stderr:
                return False
            else:
                raise
    return _try_deploy(cert_src, cert_path), _try_deploy(key_src, key_path)


def _deploy_external_cert():
    target_runtime_props = ctx.target.instance.runtime_properties

    external_cert_deployed, external_key_deployed = _deploy_cert_and_key(
        'rest_certificate', 'rest_key',
        utils.EXTERNAL_CERT_PATH, utils.EXTERNAL_KEY_PATH)

    if external_key_deployed and external_cert_deployed:
        ctx.logger.info(
            'Deployed user-provided external SSL certificate and private key')
    elif not external_cert_deployed and not external_key_deployed:
        utils.generate_ssl_certificate(
            [target_runtime_props['external_rest_host'],
             target_runtime_props['internal_rest_host']],
            target_runtime_props['external_rest_host'],
            utils.EXTERNAL_CERT_PATH,
            utils.EXTERNAL_KEY_PATH,
            sign_cert=None, sign_key=None
        )
    else:
        what_deployed = 'cert' if external_cert_deployed else 'key'
        ctx.abort_operation('Either both the external cert and the external '
                            'key must be provided, or neither. Only the {0} '
                            'was provided'.format(what_deployed))

    src_runtime_props['external_cert_path'] = utils.EXTERNAL_CERT_PATH
    src_runtime_props['external_key_path'] = utils.EXTERNAL_KEY_PATH


def preconfigure_nginx():
    # This is used by nginx's default.conf to select the relevant configuration
    target_runtime_props = ctx.target.instance.runtime_properties

    external_rest_protocol = target_runtime_props['external_rest_protocol']
    internal_rest_port = target_runtime_props['internal_rest_port']

    src_runtime_props['external_rest_protocol'] = external_rest_protocol
    src_runtime_props['internal_cert_path'] = utils.INTERNAL_CERT_PATH
    src_runtime_props['internal_key_path'] = utils.INTERNAL_KEY_PATH
    src_runtime_props['internal_rest_port'] = internal_rest_port
    src_runtime_props['file_server_root'] = utils.MANAGER_RESOURCES_HOME

    # Pass on the the path to the certificate to manager_configuration
    target_runtime_props['internal_cert_path'] = utils.INTERNAL_CA_CERT_PATH

    _deploy_external_cert()
    # The public cert content is used in the outputs later
    target_runtime_props['external_rest_cert_content'] = \
        utils.get_file_content(utils.EXTERNAL_CERT_PATH)

    _deploy_nginx_config_files()
    utils.systemd.enable(NGINX_SERVICE_NAME, append_prefix=False)


def create_certs():
    utils.mkdir(utils.SSL_CERTS_TARGET_DIR)
    ca_cert_deployed, ca_key_deployed = _deploy_cert_and_key(
        'ca_cert', 'ca_key',
        utils.INTERNAL_CA_CERT_PATH, utils.INTERNAL_CA_KEY_PATH)
    has_ca_key = ca_key_deployed
    if not ca_cert_deployed:
        if ca_key_deployed:
            ctx.abort_operation('Internal CA key provided, but the internal '
                                'CA cert was not')
        utils.generate_ca_cert()
        has_ca_key = True

    networks = \
        ctx.target.node.properties['cloudify']['cloudify_agent']['networks']
    internal_rest_host = \
        ctx.target.instance.runtime_properties['internal_rest_host']
    utils.store_cert_metadata(internal_rest_host, networks)

    internal_cert_deployed, internal_key_deployed = _deploy_cert_and_key(
        'internal_cert', 'internal_key',
        utils.INTERNAL_CERT_PATH, utils.INTERNAL_KEY_PATH)

    if not internal_cert_deployed and not internal_key_deployed:
        if not has_ca_key:
            ctx.abort_operation('Only the internal CA was provided, but not '
                                'the key - the internal cert and key must be '
                                'provided as well')
        cert_ips = [internal_rest_host] + list(networks.values())
        utils.generate_internal_ssl_cert(ips=cert_ips, name=internal_rest_host)


create_certs()
preconfigure_nginx()

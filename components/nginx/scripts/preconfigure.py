#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

CONFIG_PATH = 'components/nginx/config'
EXTERNAL_REST_CERT_PATH = '/root/cloudify/ssl/external_rest_host.crt'

NGINX_SERVICE_NAME = 'nginx'
ctx_properties = {'service_name': NGINX_SERVICE_NAME}


def preconfigure_nginx():

    target_runtime_props = ctx.target.instance.runtime_properties
    # this is used by nginx's default.conf to select the relevant configuration
    rest_protocol = target_runtime_props['rest_protocol']

    # TODO: NEED TO IMPLEMENT THIS IN CTX UTILS
    ctx.source.instance.runtime_properties['rest_protocol'] = rest_protocol
    if rest_protocol == 'https':
        utils.deploy_rest_certificates(
            internal_rest_host=target_runtime_props['internal_rest_host'],
            external_rest_host=target_runtime_props['external_rest_host'])

        # get rest public certificate for output later
        external_rest_cert_content = \
            utils.get_file_content(EXTERNAL_REST_CERT_PATH)
        target_runtime_props['external_rest_cert_content'] = \
            external_rest_cert_content

    ctx.logger.info('Deploying Nginx configuration files...')
    utils.deploy_blueprint_resource(
        '{0}/{1}-rest-server.cloudify'.format(CONFIG_PATH, rest_protocol),
        '/etc/nginx/conf.d/{0}-rest-server.cloudify'.format(rest_protocol),
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/nginx.conf'.format(CONFIG_PATH),
        '/etc/nginx/nginx.conf',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/default.conf'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/default.conf',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/rest-location.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/rest-location.cloudify',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/fileserver-location.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/fileserver-location.cloudify',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/ui-locations.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/ui-locations.cloudify',
        NGINX_SERVICE_NAME, load_ctx=False)
    utils.deploy_blueprint_resource(
        '{0}/logs-conf.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/logs-conf.cloudify',
        NGINX_SERVICE_NAME, load_ctx=False)

    utils.systemd.enable(NGINX_SERVICE_NAME,
                         append_prefix=False)


preconfigure_nginx()

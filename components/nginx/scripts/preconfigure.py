#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA
ctx_properties = {'service_name': 'nginx'}


CONFIG_PATH = 'components/nginx/config'


def preconfigure_nginx():
    ssl_resources_rel_path = 'resources/ssl'
    ssl_certs_root = '/root/cloudify'

    # this is used by nginx's default.conf to select the relevant configuration
    rest_protocol = ctx.target.instance.runtime_properties['rest_protocol']

    # TODO: NEED TO IMPLEMENT THIS IN CTX UTILS
    ctx.source.instance.runtime_properties['rest_protocol'] = rest_protocol
    if rest_protocol == 'https':
        ctx.logger.info('Copying SSL Certs...')
        utils.mkdir(ssl_certs_root)
        utils.deploy_blueprint_resource(
            '{0}/server.crt'.format(ssl_resources_rel_path),
            '{0}/server.crt'.format(ssl_certs_root),
            ctx_properties)
        utils.deploy_blueprint_resource(
            '{0}/server.key'.format(ssl_resources_rel_path),
            '{0}/server.key'.format(ssl_certs_root),
            ctx_properties)

    ctx.logger.info('Deploying Nginx configuration files...')
    utils.deploy_blueprint_resource(
        '{0}/{1}-rest-server.cloudify'.format(CONFIG_PATH, rest_protocol),
        '/etc/nginx/conf.d/{0}-rest-server.cloudify'.format(rest_protocol),
        ctx_properties)
    utils.deploy_blueprint_resource(
        '{0}/nginx.conf'.format(CONFIG_PATH),
        '/etc/nginx/nginx.conf',
        ctx_properties)
    utils.deploy_blueprint_resource(
        '{0}/default.conf'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/default.conf',
        ctx_properties)
    utils.deploy_blueprint_resource(
        '{0}/rest-location.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/rest-location.cloudify',
        ctx_properties)
    utils.deploy_blueprint_resource(
        '{0}/fileserver-location.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/fileserver-location.cloudify',
        ctx_properties)
    utils.deploy_blueprint_resource(
        '{0}/ui-locations.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/ui-locations.cloudify',
        ctx_properties)
    utils.deploy_blueprint_resource(
        '{0}/logs-conf.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/logs-conf.cloudify',
        ctx_properties)

    utils.systemd.enable('nginx')


preconfigure_nginx()

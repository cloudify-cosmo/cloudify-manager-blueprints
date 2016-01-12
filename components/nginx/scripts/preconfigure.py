#!/usr/bin/env python

from os.path import (join as jn, dirname as dn)

from cloudify import ctx

ctx.download_resource('components/utils.py', jn(dn(__file__), 'utils.py'))
import utils


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
            '{0}/server.crt'.format(ssl_certs_root))
        utils.deploy_blueprint_resource(
            '{0}/server.key'.format(ssl_resources_rel_path),
            '{0}/server.key'.format(ssl_certs_root))

    ctx.logger.info('Deploying Nginx configuration files...')
    utils.deploy_blueprint_resource(
        '{0}/{1}-rest-server.cloudify'.format(CONFIG_PATH, rest_protocol),
        '/etc/nginx/conf.d/{0}-rest-server.cloudify'.format(rest_protocol))
    utils.deploy_blueprint_resource(
        '{0}/nginx.conf'.format(CONFIG_PATH),
        '/etc/nginx/nginx.conf')
    utils.deploy_blueprint_resource(
        '{0}/default.conf'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/default.conf')
    utils.deploy_blueprint_resource(
        '{0}/rest-location.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/rest-location.cloudify')
    utils.deploy_blueprint_resource(
        '{0}/fileserver-location.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/fileserver-location.cloudify')
    utils.deploy_blueprint_resource(
        '{0}/ui-locations.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/ui-locations.cloudify')
    utils.deploy_blueprint_resource(
        '{0}/logs-conf.cloudify'.format(CONFIG_PATH),
        '/etc/nginx/conf.d/logs-conf.cloudify')

    utils.systemd.enable('nginx')


preconfigure_nginx()

#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


runtime_props = ctx.instance.runtime_properties
SERVICE_NAME = runtime_props['service_name']

ctx_properties = utils.ctx_factory.get(SERVICE_NAME)
CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)
RIEMANN_CONFIG_PATH = '/etc/riemann'


def get_manager_config():
    """
    Extracting specific files from cloudify-manager repo, with clean-ups after
    """
    cloudify_resources_url = ctx_properties['cloudify_resources_url']

    ctx.logger.info('Downloading cloudify-manager Repository...')
    manager_repo = utils.download_cloudify_resource(
        cloudify_resources_url, SERVICE_NAME)
    ctx.logger.info('Extracting Manager Repository...')
    manager_dir = utils.untar(manager_repo, unique_tmp_dir=True)

    ctx.logger.info('Deploying Riemann manager.config...')
    config_src_path = join(
        manager_dir, 'plugins', 'riemann-controller',
        'riemann_controller', 'resources', 'manager.config'
    )
    utils.move(
        config_src_path,
        '{0}/conf.d/manager.config'.format(RIEMANN_CONFIG_PATH)
    )
    utils.remove(manager_dir)
    utils.remove(manager_repo)


def configure_riemann():
    ctx.logger.info('Deploying Riemann conf...')
    utils.deploy_blueprint_resource(
        '{0}/main.clj'.format(CONFIG_PATH),
        '{0}/main.clj'.format(RIEMANN_CONFIG_PATH),
        SERVICE_NAME)

    utils.chown(
        runtime_props['service_user'],
        runtime_props['service_group'],
        RIEMANN_CONFIG_PATH
    )

    # our riemann configuration will (by default) try to read these environment
    # variables. If they don't exist, it will assume
    # that they're found at "localhost"
    # export REST_HOST=""
    # export RABBITMQ_HOST=""

    # we inject the management_ip for both of these to Riemann's systemd
    # config.
    # These should be potentially different
    # if the manager and rabbitmq are running on different hosts.
    utils.systemd.configure(SERVICE_NAME)
    utils.clean_var_log_dir(SERVICE_NAME)


get_manager_config()
configure_riemann()

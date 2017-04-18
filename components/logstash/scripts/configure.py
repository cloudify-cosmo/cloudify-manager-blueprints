#!/usr/bin/env python

from os.path import (
    dirname,
    join,
)

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties
SERVICE_NAME = runtime_props['service_name']

INIT_D_FILE = '/etc/init.d/logstash'
LOGSTASH_CONF_PATH = '/etc/logstash/conf.d'
utils.extend_runtime_properties_list(
    runtime_props,
    'files_to_remove',
    [INIT_D_FILE, '/etc/logstash']
)

CONFIG_PATH = 'components/{0}/config'.format(SERVICE_NAME)


def configure_logstash():
    rabbitmq_username = runtime_props.get('rabbitmq_username')
    rabbitmq_password = runtime_props.get('rabbitmq_password')

    # Confirm username and password have been supplied for broker before
    # continuing.
    # Components other than logstash and riemann have this handled in code.
    # Note that these are not directly used in this script, but are used by the
    # deployed resources, hence the check here.
    if not rabbitmq_username or not rabbitmq_password:
        ctx.abort_operation(
            'Both rabbitmq_username and rabbitmq_password must be supplied '
            'and at least 1 character long in the manager blueprint inputs.')

    ctx.logger.info('Deploying Logstash configuration...')
    utils.deploy_blueprint_resource(
        '{0}/logstash.conf'.format(CONFIG_PATH),
        '{0}/logstash.conf'.format(LOGSTASH_CONF_PATH),
        SERVICE_NAME)

    # Due to a bug in the handling of configuration files,
    # configuration files with the same name cannot be deployed.
    # Since the logrotate config file is called `logstash`,
    # we change the name of the logstash env vars config file
    # from logstash to cloudify-logstash to be consistent with
    # other service env var files.
    utils.replace_in_file(
        'sysconfig/\$name',
        'sysconfig/cloudify-$name',
        INIT_D_FILE)
    utils.chmod('755', INIT_D_FILE)
    utils.chown('root', 'root', INIT_D_FILE)

    ctx.logger.debug('Deploying Logstash sysconfig...')
    utils.deploy_blueprint_resource(
        '{0}/cloudify-logstash'.format(CONFIG_PATH),
        '/etc/sysconfig/cloudify-logstash',
        SERVICE_NAME)

    utils.logrotate(SERVICE_NAME)
    utils.sudo(['/sbin/chkconfig', 'logstash', 'on'])
    utils.clean_var_log_dir(SERVICE_NAME)


if __name__ == '__main__':
    configure_logstash()

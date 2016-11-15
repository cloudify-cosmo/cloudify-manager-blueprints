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


CONFIG_PATH = 'components/logstash/config'
LOGSTASH_SERVICE_NAME = 'logstash'


def configure_logstash():

    logstash_conf_path = '/etc/logstash/conf.d'

    ctx.logger.info('Deploying Logstash configuration...')
    utils.deploy_blueprint_resource(
        '{0}/logstash.conf'.format(CONFIG_PATH),
        '{0}/logstash.conf'.format(logstash_conf_path),
        LOGSTASH_SERVICE_NAME)

    # Due to a bug in the handling of configuration files,
    # configuration files with the same name cannot be deployed.
    # Since the logrotate config file is called `logstash`,
    # we change the name of the logstash env vars config file
    # from logstash to cloudify-logstash to be consistent with
    # other service env var files.
    init_file = '/etc/init.d/logstash'
    utils.replace_in_file(
        'sysconfig/\$name',
        'sysconfig/cloudify-$name',
        init_file)
    utils.chmod('755', init_file)
    utils.chown('root', 'root', init_file)

    ctx.logger.debug('Deploying Logstash sysconfig...')
    utils.deploy_blueprint_resource(
        '{0}/cloudify-logstash'.format(CONFIG_PATH),
        '/etc/sysconfig/cloudify-logstash',
        LOGSTASH_SERVICE_NAME)

    utils.logrotate(LOGSTASH_SERVICE_NAME)
    utils.sudo(['/sbin/chkconfig', 'logstash', 'on'])
    utils.clean_var_log_dir(LOGSTASH_SERVICE_NAME)


if __name__ == '__main__':
    configure_logstash()

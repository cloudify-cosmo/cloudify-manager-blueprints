#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

RIEMANN_SERVICE_NAME = 'riemann'

ctx_properties = utils.ctx_factory.create(RIEMANN_SERVICE_NAME)
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = RIEMANN_SERVICE_NAME
runtime_props['service_user'] = RIEMANN_SERVICE_NAME
runtime_props['service_group'] = RIEMANN_SERVICE_NAME
RIEMANN_USER = RIEMANN_SERVICE_NAME
RIEMANN_GROUP = RIEMANN_SERVICE_NAME


def install_riemann():
    langohr_source_url = ctx_properties['langohr_jar_source_url']
    daemonize_source_url = ctx_properties['daemonize_rpm_source_url']
    riemann_source_url = ctx_properties['riemann_rpm_source_url']

    rabbitmq_username = ctx_properties['rabbitmq_username']
    rabbitmq_password = ctx_properties['rabbitmq_password']

    utils.create_service_user(
        user=RIEMANN_USER,
        group=RIEMANN_GROUP,
        home=utils.CLOUDIFY_HOME_DIR
    )

    riemann_config_path = '/etc/riemann'
    riemann_log_path = '/var/log/cloudify/riemann'
    langohr_home = '/opt/lib'
    extra_classpath = '{0}/langohr.jar'.format(langohr_home)
    riemann_dir = '/opt/riemann'

    # Confirm username and password have been supplied for broker before
    # continuing.
    # Components other than logstash and riemann have this handled in code.
    # Note that these are not directly used in this script, but are used by the
    # deployed resources, hence the check here.
    if not rabbitmq_username or not rabbitmq_password:
        ctx.abort_operation(
            'Both rabbitmq_username and rabbitmq_password must be supplied '
            'and at least 1 character long in the manager blueprint inputs.')

    rabbit_props = utils.ctx_factory.get('rabbitmq')
    runtime_props['rabbitmq_endpoint_ip'] = utils.get_rabbitmq_endpoint_ip()
    runtime_props['rabbitmq_username'] = rabbit_props.get('rabbitmq_username')
    runtime_props['rabbitmq_password'] = rabbit_props.get('rabbitmq_password')

    ctx.logger.info('Installing Riemann...')
    utils.set_selinux_permissive()

    utils.copy_notice(RIEMANN_SERVICE_NAME)
    utils.mkdir(riemann_log_path)
    utils.mkdir(langohr_home)
    utils.mkdir(riemann_config_path)
    utils.mkdir('{0}/conf.d'.format(riemann_config_path))

    # utils.chown cannot be used as it will change both user and group
    utils.sudo(['chown', RIEMANN_USER, riemann_dir])

    langohr = utils.download_cloudify_resource(langohr_source_url,
                                               RIEMANN_SERVICE_NAME)
    utils.sudo(['cp', langohr, extra_classpath])
    ctx.logger.info('Applying Langohr permissions...')
    utils.sudo(['chmod', '644', extra_classpath])
    utils.yum_install(daemonize_source_url, service_name=RIEMANN_SERVICE_NAME)
    utils.yum_install(riemann_source_url, service_name=RIEMANN_SERVICE_NAME)

    utils.chown(RIEMANN_USER, RIEMANN_GROUP, riemann_log_path)

    utils.logrotate(RIEMANN_SERVICE_NAME)

    files_to_remove = [riemann_config_path,
                       riemann_log_path,
                       extra_classpath,
                       riemann_dir]
    runtime_props['files_to_remove'] = files_to_remove


install_riemann()

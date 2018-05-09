#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx
from cloudify_rest_client import CloudifyClient
from cloudify_rest_client.exceptions import CloudifyClientError

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


BLUEPRINT_ID = 'sanity_bp'
DEPLOYMENT_ID = 'sanity_deployment'
SERVICE_NAME = 'sanity'

# Some runtime properties to be used in teardown
runtime_props = ctx.instance.runtime_properties
runtime_props['service_name'] = SERVICE_NAME

manager_remote_key_path = runtime_props['manager_remote_key_path']
ctx_properties = ctx.node.properties.get_all()


def wait_for_workflow(client, deployment_id, workflow_id):
    executions = client.executions.list(deployment_id=deployment_id)
    for execution in executions:
        if execution.workflow_id == workflow_id:
            execution_status = execution.status
            if execution_status == 'terminated':
                return True
            elif execution_status == 'failed':
                ctx.abort_operation('Execution with id {0} failed'.
                                    format(execution.id))
    return False


def _prepare_sanity_app(client):
    _upload_app_blueprint(client)
    _deploy_app(client)


def _upload_app_blueprint(client):
    if _is_sanity_blueprint_exist(client):
        return
    sanity_app_source_url = ctx_properties['sanity_app_source_url']
    app_tar = utils.download_cloudify_resource(
        url=sanity_app_source_url,
        service_name=SERVICE_NAME)
    client.blueprints.publish_archive(
        app_tar, blueprint_id=BLUEPRINT_ID,
        blueprint_filename='no-monitoring-singlehost-blueprint.yaml')


def _deploy_app(client):
    if _is_sanity_dep_exist(client):
        return

    client.deployments.create(BLUEPRINT_ID, DEPLOYMENT_ID, inputs={
        'server_ip': '127.0.0.1',
        'agent_user': os.environ.get('ssh_user'),
        'agent_private_key_path': manager_remote_key_path
    })

    # Waiting for create deployment env to end
    utils.repetitive(
        wait_for_workflow,
        client=client,
        deployment_id=DEPLOYMENT_ID,
        workflow_id='create_deployment_environment',
        timeout=60,
        timeout_msg='Timed out while waiting for '
                    'deployment {0} to be created'.format(DEPLOYMENT_ID))


def _install_sanity_app(client):
    execution = client.executions.start(DEPLOYMENT_ID, 'install')
    utils.repetitive(
        wait_for_workflow,
        client=client,
        deployment_id=DEPLOYMENT_ID,
        workflow_id='install',
        timeout=5 * 60,
        interval=5,
        timeout_msg='Timed out while waiting for '
                    'deployment {0} to install'.format(DEPLOYMENT_ID))
    return execution.id


def _assert_logs_and_events(client, execution_id):
    events = client.events.get(execution_id, include_logs=True)
    if len(events) <= 0:
        ctx.abort_operation('No logs/events received')


def _assert_webserver_running():
    resp = utils.http_request(
        'http://localhost:8080',
        method='GET',
        timeout=10)

    if not resp:
        ctx.abort_operation("Can't connect to webserver")
    if resp.code != 200:
        ctx.abort_operation('Sanity app webserver failed to start')


def _cleanup_sanity(client):
    _uninstall_sanity_app(client)
    _delete_sanity_deployment(client)
    _delete_sanity_blueprint(client)
    _delete_key_file()


def _uninstall_sanity_app(client):
    if not _is_sanity_dep_exist(client):
        return

    client.executions.start(DEPLOYMENT_ID, 'uninstall')
    # Waiting for uninstallation to complete
    utils.repetitive(
        wait_for_workflow,
        client=client,
        deployment_id=DEPLOYMENT_ID,
        workflow_id='uninstall',
        timeout=5 * 60,
        interval=5,
        timeout_msg='Timed out while waiting for '
                    'deployment {0} to uninstall'.format(DEPLOYMENT_ID))


def _delete_sanity_deployment(client):
    if not _is_sanity_dep_exist(client):
        return
    client.deployments.delete(DEPLOYMENT_ID)


def _delete_sanity_blueprint(client):
    if not _is_sanity_blueprint_exist(client):
        return
    client.blueprints.delete(BLUEPRINT_ID)


def _delete_key_file():
    if os.path.isfile(manager_remote_key_path):
        os.remove(manager_remote_key_path)


def _is_sanity_dep_exist(client):
    try:
        client.deployments.get(DEPLOYMENT_ID)
    except CloudifyClientError as e:
        if e.status_code != 404:
            raise
        return False
    else:
        return True


def _is_sanity_blueprint_exist(client):
    try:
        client.blueprints.get(BLUEPRINT_ID)
    except CloudifyClientError as e:
        if e.status_code != 404:
            raise
        return False
    else:
        return True


def perform_sanity():
    security_config = runtime_props['security_configuration']
    username = security_config['admin_username']
    password = security_config['admin_password']
    client = CloudifyClient(
        port=runtime_props['rest_port'],
        protocol=runtime_props['rest_protocol'],
        cert=utils.INTERNAL_CA_CERT_PATH,
        username=username, password=password, tenant='default_tenant')

    ctx.logger.info('Starting Manager sanity check...')
    _prepare_sanity_app(client)
    ctx.logger.info('Installing sanity app...')
    exec_id = _install_sanity_app(client)
    ctx.logger.info('Sanity app installed. Performing sanity test...')
    _assert_webserver_running()
    _assert_logs_and_events(client, exec_id)
    ctx.logger.info('Manager sanity check successful, '
                    'cleaning up sanity resources.')
    _cleanup_sanity(client)


# the 'run_sanity' parameter is injected explicitly from the cli as an
# operation parameter with 'true' as its value.
# This is done to prevent the sanity test from running before the
# provider context is available.
if os.environ.get('run_sanity') == 'true':
    perform_sanity()

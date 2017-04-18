#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

runtime_props = ctx.instance.runtime_properties
SERVICE_NAME = runtime_props['service_name']
HOME_DIR = runtime_props['home_dir']


@utils.retry(ValueError)
def check_worker_running():
    """Use `celery status` to check if the worker is running."""
    work_dir = join(HOME_DIR, 'work')
    celery_path = join(HOME_DIR, 'env', 'bin', 'celery')
    result = utils.sudo([
        'CELERY_WORK_DIR={0}'.format(work_dir),
        celery_path,
        '--config=cloudify.broker_config',
        'status'
    ], ignore_failures=True)
    if result.returncode != 0:
        raise ValueError('celery status: worker not running')


ctx.logger.info('Starting Management Worker Service...')
utils.start_service(SERVICE_NAME)

utils.systemd.verify_alive(SERVICE_NAME)

try:
    check_worker_running()
except ValueError:
    ctx.abort_operation('Celery worker failed to start')

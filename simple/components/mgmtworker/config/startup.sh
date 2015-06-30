#!/bin/bash

# Startup all celeryd
shopt -s nullglob
for f in /etc/init.d/celeryd-*
do
    /usr/sbin/service ${f##*/} start
done

# Start managment worker
${VIRTUALENV_DIR}/bin/celery worker \
    -Ofair
    --include=cloudify_system_workflows.deployment_environment,plugin_installer.tasks,worker_installer.tasks,riemann_controller.tasks,cloudify.plugins.workflows \
    --broker=${BROKER_URL} \
    --hostname celery.cloudify.management \
    --events \
    --app=cloudify \
    --loglevel=debug \
    --queues=cloudify.management \
    --logfile=${CELERY_LOG_DIR}/cloudify.management_worker.log \
    --pidfile=${CELERY_LOG_DIR}/cloudify.management_worker.pid \
    --autoscale=5,2 \
    --without-gossip \
    --without-mingle

#!/bin/bash

export MGMTWORKER_HOME="/opt/mgmtworker"
export VIRTUALENV_DIR="${MGMTWORKER_HOME}/env"
export CELERY_WORK_DIR="${MGMTWORKER_HOME}/work"
export CELERY_LOG_DIR="/var/log/cloudify/mgmtworker"
export RIEMANN_CONFIGS_DIR="/opt/riemann"
export MANAGEMENT_IP="localhost"
export BROKER_URL="amqp://guest:guest@localhost:5672/"
export MANAGEMENT_USER="root"
export MANAGER_REST_PORT="8100"
export MANAGER_FILE_SERVER_URL="http://localhost:53229"
export MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL="http://localhost:53229/blueprints"
export CELERY_TASK_SERIALIZER="json"
export CELERY_RESULT_SERIALIZER="json"
export CELERY_RESULT_BACKEND="amqp"
export C_FORCE_ROOT=true


sudo -E ${VIRTUALENV_DIR}/bin/celery worker \
-Ofair \
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
--without-mingle &
# sudo ${MGMTWORKER_HOME}/startup.sh
#!/bin/bash -e

export REST_SERVICE_HOME=/opt/manager
export REST_SERVICE_VIRTUALENV=${REST_SERVICE_HOME}/env
export MANAGER_VIRTUALENV=${REST_SERVICE_HOME}/env
export REST_SERVICE_LOG_PATH=/var/log/cloudify/rest
export MANAGER_REST_CONFIG_PATH=${REST_SERVICE_HOME}/guni.conf
# export REST_SERVICE_PORT=$(ctx node properties rest_service_port)
export REST_SERVICE_PORT="8100"

WORKERS=$(($(nproc)*2+1))

ctx logger info "Starting Rest Service via Gunicorn using ${WORKERS} workers..."
sudo -E ${REST_SERVICE_VIRTUALENV}/bin/gunicorn \
    -w ${WORKERS} \
    -b 0.0.0.0:${REST_SERVICE_PORT} \
    --timeout 300 manager_rest.server:app \
    --log-file ${REST_SERVICE_LOG_PATH}/gunicorn.log \
    --access-logfile ${MANAGER_REST_LOG_PATH}/gunicorn-access.log > /dev/null 2>&1 &

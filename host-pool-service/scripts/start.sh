#!/bin/bash


_APPLICATION_PATH=cloudify_hostpool.rest.service:app


_error(){
    echo "$1" 1>&2
    exit 1
}


[ -z "${HOST_POOL_CONFIG}" ] && HOST_POOL_CONFIG=host-pool.yaml
[ -z "${NUM_WORKERS}" ] && NUM_WORKERS=5
[ -z "${PID_FILE}" ] && PID_FILE=gunicorn.pid
[ -z "${LOG_LEVEL}" ] && LOG_LEVEL=INFO
[ -z "${LOG_FILE}" ] && LOG_FILE=gunicorn.log
[ -z "${BIND_INTERFACE}" ] && BIND_INTERFACE=0.0.0.0

[ -r "${HOST_POOL_CONFIG}" ] || \
    _error "Host pool's configuration file '${HOST_POOL_CONFIG}' either does not exist or is inaccessible!"

set -e
. bin/activate
HOST_POOL_SERVICE_CONFIG_PATH="${HOST_POOL_CONFIG}" \
    gunicorn \
        --workers="${NUM_WORKERS}" \
        --pid="${PID_FILE}" \
        --worker-tmp-dir=/tmp \
        --log-level="${LOG_LEVEL}" \
        --log-file="${LOG_FILE}" \
        --bind "${BIND_INTERFACE}" \
        --daemon \
        "${_APPLICATION_PATH}"

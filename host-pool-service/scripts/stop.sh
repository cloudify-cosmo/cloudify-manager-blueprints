#!/bin/bash


_RETRY_COUNT=5
_SLEEP_TIME=0.33


_error(){
    echo "$1" 1>&2
    exit 1
}


_process_exists(){
    ps -p$1 1>/dev/null 2>&1
    return $?
}


_sleep(){
    python -c "import time; time.sleep($_SLEEP_TIME)"
}


[ -z "${PID_FILE}" ] && PID_FILE=gunicorn.pid

[ -r "${PID_FILE}" ] || \
    _error "PID file '${PID_FILE}' is inaccessible or does not exist!"

declare -r pid=$(cat "${PID_FILE}")

[[ ${pid} =~ ^[0-9]+$ ]] || _error "Invalid PID file's '${PID_FILE}' format."

for s in 2 15; do
    _process_exists ${pid} || exit 0
    kill -${s} ${pid}
    i=0
    while [ $i -lt ${_RETRY_COUNT} ]; do
        _process_exists ${pid} || exit 0
        [ ${i} -lt 5 ] && _sleep ${_SLEEP_TIME}
        ((++i))
    done
done
_process_exists ${pid} && kill -9 ${pid}

[ -f "${PID_FILE}" ] && rm -vf "${PID_FILE}"

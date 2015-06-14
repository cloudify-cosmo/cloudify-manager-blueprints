#!/bin/bash -e

export RIEMANN_CONFIG_PATH="/etc/riemann"
export LANGOHR_HOME="/opt/lib"
export EXTRA_CLASSPATH="${LANGOHR_HOME}/langohr.jar"

ctx logger info "Starting Riemann..."
sudo -E /usr/bin/riemann -a ${RIEMANN_CONFIG_PATH}/main.clj > /dev/null 2>&1 &

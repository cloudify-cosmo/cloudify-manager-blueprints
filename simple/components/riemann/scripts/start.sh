#!/bin/bash

export RIEMANN_CONFIG_PATH="/etc/riemann"
export LANGOHR_HOME="/opt/lib"
export EXTRA_CLASSPATH="${LANGOHR_HOME}/langohr.jar"

function main
{
    sudo -E /usr/bin/riemann -a ${RIEMANN_CONFIG_PATH}/main.clj &
}

main

#!/bin/bash

RIEMANN_VERSION="0.2.6"
LANGOHR_VERSION="2.11.0"
RIEMANN_CONFIG_PATH="/etc/riemann"
RIEMANN_LOG_PATH="/var/log/cloudify/riemann"
LANGOHR_HOME="/opt/lib"
EXTRA_CLASSPATH="${LANGOHR_HOME}/langohr.jar"
# LANGOHR_SOURCE_URL=$(ctx node properties langohr_jar_source_url)
LANGOHR_SOURCE_URL="https://s3-eu-west-1.amazonaws.com/gigaspaces-repository-eu/langohr/${LANGOHR_VERSION}/langohr.jar"
# DAEMONIZE_SOURCE_URL=$(ctx node properties daemonize_rpm_source_url)
DAEMONIZE_SOURCE_URL="https://forensics.cert.org/centos/cert/7/x86_64/daemonize-1.7.3-7.el7.x86_64.rpm"
# RIEMANN_SOURCE_URL=$(ctx node properties riemann_rpm_source_url)
RIEMANN_SOURCE_URL="https://aphyr.com/riemann/riemann-${RIEMANN_VERSION}-1.noarch.rpm"

# if java isn't installed via an rpm, the path should be set so that Riemann can use it
# export PATH="$PATH:/opt/java/bin"
# our riemann configuration will (by default) try to read this environment variable. If it doesn't exist, it will assume
# nginx is found in "localhost"
# export MANAGEMENT_IP=""
# our riemann configuration will (by default) try to read this environment variable. If it doesn't exist, it will assume
# rabbitmq is found in "localhost"
# export RABBITMQ_HOST=""

# we should definitely make out another way of retrieving this. maybe by downloading the same version of the rest service's repo tar
RIEMANN_MASTER_CONFIG_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-manager/master/plugins/riemann-controller/riemann_controller/resources/manager.config"


function import_helpers
{
    if [ ! -e "/tmp/utils" ]; then
        cp components/utils /tmp/utils
        # ctx download-resource "components/utils" '@{"target_path": "/tmp/utils"}'
    fi
    . /tmp/utils
    # required only in current vagrant environment otherwise passed to the vm via the script plugin
    . components/env_vars
}

function main
{
    log_section "Installing Riemann..."

    copy_notice "riemann"
    create_dir ${RIEMANN_LOG_PATH} && \
    create_dir ${EXTRA_CLASSPATH} && \
    create_dir ${RIEMANN_CONFIG_PATH} && \
    create_dir ${RIEMANN_CONFIG_PATH}/conf.d && \

    download_file ${LANGOHR_SOURCE_URL} "/tmp/langohr.jar" && \
    sudo mv "/tmp/langohr.jar" ${LANGOHR_HOME} && \
    sudo chmod 644 ${EXTRA_CLASSPATH} && \
    sudo yum install -y ${DAEMONIZE_SOURCE_URL}
    install_rpm ${RIEMANN_SOURCE_URL} && \

    download_file ${RIEMANN_MASTER_CONFIG_URL} "/tmp/manager.config" && \
    sudo mv /tmp/manager.config ${RIEMANN_CONFIG_PATH}/conf.d/manager.config && \
    sudo cp components/riemann/config/main.clj ${RIEMANN_CONFIG_PATH}/
}

cd /vagrant
import_helpers
main
#!/bin/bash -e

export DSL_PARSER_VERSION=3.2
export REST_CLIENT_VERSION=3.2
export PLUGINS_COMMON_VERSION=3.2
export REST_SERVICE_VERSION=3.2
export SECUREST_VERSION=0.6
# TODO: change to /opt/cloudify-rest-service
export REST_SERVICE_HOME=/opt/manager
export REST_SERVICE_VIRTUALENV=${REST_SERVICE_HOME}/env
# guni.conf currently contains localhost for all endpoints. We need to change that.
# this is mandatory since the manager's code reads this env var. it should be named as below.
export MANAGER_REST_CONFIG_PATH=${REST_SERVICE_HOME}/guni.conf
export REST_SERVICE_CONFIG_PATH=${REST_SERVICE_HOME}/guni.conf
export REST_SERVICE_LOG_PATH=/var/log/cloudify/rest
# export DSL_PARSER_SOURCE_URL=$(ctx node properties dsl_parser_module_source_url)
export DSL_PARSER_SOURCE_URL="https://github.com/cloudify-cosmo/cloudify-dsl-parser/archive/${DSL_PARSER_VERSION}.tar.gz"
# export REST_CLIENT_SOURCE_URL=$(ctx node properties rest_client_module_source_url)
export REST_CLIENT_SOURCE_URL="https://github.com/cloudify-cosmo/cloudify-rest-client/archive/${REST_CLIENT_VERSION}.tar.gz"
# export PLUGINS_COMMON_SOURCE_URL=$(ctx node properties plugins_common_module_source_url)
export PLUGINS_COMMON_SOURCE_URL="https://github.com/cloudify-cosmo/cloudify-plugins-common/archive/${PLUGINS_COMMON_VERSION}.tar.gz"
# export SECUREST_SOURCE_URL=$(ctx node properties securest_module_source_url)
export SECUREST_SOURCE_URL="https://github.com/cloudify-cosmo/flask-securest/archive/${SECUREST_VERSION}.tar.gz"
# export REST_SERVICE_SOURCE_URL=$(ctx node properties rest_service_module_source_url)
export REST_SERVICE_SOURCE_URL="https://github.com/cloudify-cosmo/cloudify-manager/archive/${REST_SERVICE_VERSION}.tar.gz"


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
    ctx logger info "Installing REST Service..."

    copy_notice "restservice"
    create_dir ${REST_SERVICE_HOME} &&
    create_dir ${REST_SERVICE_LOG_PATH} &&

    ctx logger info "Creating virtualenv ${REST_SERVICE_VIRTUALENV}..."
    create_virtualenv ${REST_SERVICE_VIRTUALENV}

    ctx logger info "Installing Required REST Service Modules..."
    install_module ${DSL_PARSER_SOURCE_URL} ${REST_SERVICE_VIRTUALENV}
    install_module ${REST_CLIENT_SOURCE_URL} ${REST_SERVICE_VIRTUALENV}
    install_module ${PLUGINS_COMMON_SOURCE_URL} ${REST_SERVICE_VIRTUALENV}
    install_module ${SECUREST_SOURCE_URL} ${REST_SERVICE_VIRTUALENV}
    ctx logger info "Downloading Manager Repository..."
    curl --fail --insecure -L ${REST_SERVICE_SOURCE_URL} --create-dirs -o /tmp/cloudify-manager/manager.tar.gz
    ctx logger info "Extracting Manager..."
    tar -xzf /tmp/cloudify-manager/manager.tar.gz --strip-components=1 -C /tmp/cloudify-manager/
    install_module "/tmp/cloudify-manager/rest-service" ${REST_SERVICE_VIRTUALENV}
    clean_tmp

    ctx logger info "Deploying Gunicorn and REST Service Configuration file..."
    cp "components/restservice/config/guni.conf" "/tmp/guni.conf"
    # ctx download-resource components/restservice/config/guni.conf '@{"target_path": "/tmp/config.toml"}'
    sudo mv "/tmp/guni.conf" "${REST_SERVICE_HOME}/guni.conf"
}

cd /vagrant
import_helpers
main
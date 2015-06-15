#!/bin/bash -e

export CELERY_VERSION=$(ctx node properties celery_version)  # (e.g. 3.1.17)
export REST_CLIENT_SOURCE_URL=$(ctx node properties rest_client_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-rest-client/archive/3.2.zip")
export PLUGINS_COMMON_SOURCE_URL=$(ctx node properties plugins_common_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-plugins-common/archive/3.2.zip")
export SCRIPT_PLUGIN_SOURCE_URL=$(ctx node properties script_plugin_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-script-plugin/archive/1.2.zip")
export REST_SERVICE_SOURCE_URL=$(ctx node properties rest_service_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-manager/archive/3.2.tar.gz")


# these must all be exported as part of the start operation. they will not persist, so we should use the new agent
# don't forget to change all localhosts to the relevant ips
export MGMTWORKER_HOME="/opt/mgmtworker"
export VIRTUALENV_DIR="${MGMTWORKER_HOME}/env"
export CELERY_WORK_DIR="${MGMTWORKER_HOME}/work"
export CELERY_LOG_DIR="/var/log/cloudify/mgmtworker"


function import_helpers
{
    if [ ! -e "/tmp/utils" ]; then
        cp components/utils /tmp/utils
        # ctx download-resource "components/utils" '@{"target_path": "/tmp/utils"}'
    fi
    . /tmp/utils
}

function main
{
    ctx logger info "Installing Management Worker..."

    copy_notice "mgmtworker" && \
    create_dir ${MGMTWORKER_HOME} && \
    create_dir ${MGMTWORKER_HOME}/config && \
    create_dir ${CELERY_LOG_DIR} && \
    create_dir ${CELERY_WORK_DIR} && \

    ctx logger info "Creating virtualenv ${VIRTUALENV_DIR}..."
    create_virtualenv "${VIRTUALENV_DIR}" && \

    ctx logger info "Deploying mgmtworker startup script..."
    sudo cp "components/mgmtworker/config/startup.sh" "${MGMTWORKER_HOME}/startup.sh" && \
    sudo chmod +x ${MGMTWORKER_HOME}/startup.sh && \

    ctx logger info "Installing Prerequisites..."
    # instead of installing these, our build process should create wheels of the required dependencies which could be later installed directory
    sudo yum install -y python-devel g++ gcc # libxslt-dev libxml2-dev

    ctx logger info "Installing Management Worker Modules..."
    install_module "celery==${CELERY_VERSION}" ${VIRTUALENV_DIR} && \
    install_module ${REST_CLIENT_SOURCE_URL} ${VIRTUALENV_DIR} && \
    install_module ${REST_CLIENT_SOURCE_URL} ${VIRTUALENV_DIR} && \
    install_module ${REST_CLIENT_SOURCE_URL} ${VIRTUALENV_DIR} && \

    ctx logger info "Downloading Manager Repository..."
    curl -L ${REST_SERVICE_SOURCE_URL} -o /tmp/cloudify-manager.tar.gz && \
    ctx logger info "Extracting Manager Repository..."
    tar -xzf /tmp/cloudify-manager.tar.gz -C /tmp --strip-components=1 && \

    ctx logger info "Installing Management Worker Plugins..."
    install_module "/tmp/plugins/plugin-installer" ${VIRTUALENV_DIR} && \
    install_module "/tmp/plugins/agent-installer" ${VIRTUALENV_DIR} && \
    install_module "/tmp/plugins/riemann-controller" ${VIRTUALENV_DIR} && \
    install_module "/tmp/workflows" ${VIRTUALENV_DIR} && \

    ctx logger info "Cleaning up unneeded packages..."
    sudo yum remove -y python-devel g++ gcc
    clean_tmp
}

cd /vagrant
import_helpers
main
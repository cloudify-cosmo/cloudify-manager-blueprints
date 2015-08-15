#!/bin/bash -e

. $(ctx download-resource "components/utils")


export CELERY_VERSION=$(ctx node properties celery_version)  # (e.g. 3.1.17)
export REST_CLIENT_SOURCE_URL=$(ctx node properties rest_client_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-rest-client/archive/3.2.zip")
export PLUGINS_COMMON_SOURCE_URL=$(ctx node properties plugins_common_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-plugins-common/archive/3.2.zip")
export SCRIPT_PLUGIN_SOURCE_URL=$(ctx node properties script_plugin_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-script-plugin/archive/1.2.zip")
export REST_SERVICE_SOURCE_URL=$(ctx node properties rest_service_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-manager/archive/3.2.tar.gz")
export DIAMOND_PLUGIN_SOURCE_URL=$(ctx node properties diamond_plugin_module_source_url)
export AGENT_SOURCE_URL=$(ctx node properties agent_module_source_url)

# these must all be exported as part of the start operation. they will not persist, so we should use the new agent
# don't forget to change all localhosts to the relevant ips
export MGMTWORKER_HOME="/opt/mgmtworker"
export VIRTUALENV_DIR="${MGMTWORKER_HOME}/env"
export CELERY_WORK_DIR="${MGMTWORKER_HOME}/work"
export CELERY_LOG_DIR="/var/log/cloudify/mgmtworker"


ctx logger info "Installing Management Worker..."

copy_notice "mgmtworker"
create_dir ${MGMTWORKER_HOME}
create_dir ${MGMTWORKER_HOME}/config
create_dir ${CELERY_LOG_DIR}
create_dir ${CELERY_WORK_DIR}

create_virtualenv "${VIRTUALENV_DIR}"

# NOT SURE WE NEED THIS ANYMORE...
# ctx logger info "Deploying mgmtworker startup script..."
# sudo cp "components/mgmtworker/config/startup.sh" "${MGMTWORKER_HOME}/startup.sh"
# sudo chmod +x ${MGMTWORKER_HOME}/startup.sh

ctx logger info "Installing Management Worker Modules..."
install_module "celery==${CELERY_VERSION}" ${VIRTUALENV_DIR}
install_module ${REST_CLIENT_SOURCE_URL} ${VIRTUALENV_DIR}
install_module ${PLUGINS_COMMON_SOURCE_URL} ${VIRTUALENV_DIR}
# Currently cloudify-agent requires the script and diamond plugins
# so we must install them here. The mgmtworker doesn't use them.
install_module ${SCRIPT_PLUGIN_SOURCE_URL} ${VIRTUALENV_DIR}
install_module ${DIAMOND_PLUGIN_SOURCE_URL} ${VIRTUALENV_DIR}
install_module ${AGENT_SOURCE_URL} ${VIRTUALENV_DIR}

ctx logger info "Downloading cloudify-manager Repository..."
manager_repo=$(download_file ${REST_SERVICE_SOURCE_URL})
ctx logger info "Extracting Manager Repository..."
tar -xzvf ${manager_repo} --strip-components=1 -C "/tmp" >/dev/null

ctx logger info "Installing Management Worker Plugins..."
# shouldn't we extract the riemann-controller and workflows modules to their own repos?
install_module "/tmp/plugins/riemann-controller" ${VIRTUALENV_DIR}
install_module "/tmp/workflows" ${VIRTUALENV_DIR}

configure_systemd_service "mgmtworker"
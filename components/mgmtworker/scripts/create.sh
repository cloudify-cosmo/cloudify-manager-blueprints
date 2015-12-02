#!/bin/bash -e

. $(ctx download-resource "components/utils")

CONFIG_REL_PATH="components/mgmtworker/config"

export MANAGEMENT_WORKER_RPM_SOURCE_URL=$(ctx node properties management_worker_rpm_source_url)
export REST_CLIENT_SOURCE_URL=$(ctx node properties rest_client_module_source_url)
export PLUGINS_COMMON_SOURCE_URL=$(ctx node properties plugins_common_module_source_url)
export SCRIPT_PLUGIN_SOURCE_URL=$(ctx node properties script_plugin_module_source_url)
export REST_SERVICE_SOURCE_URL=$(ctx node properties rest_service_module_source_url)
export AGENT_SOURCE_URL=$(ctx node properties agent_module_source_url)
export SSH_KEY_FILE=$(ctx node properties ssh_key_filename)
export AGENT_USER=$(ctx node properties agents_user)

# This will only be used if the management worker is not installed via an RPM
export CELERY_VERSION="3.1.17"

export MGMTWORKER_USER='cloudifymgmtworker'
export MGMTWORKER_GROUP='cloudifymgmtworker'
export MGMTWORKER_HOME="/opt/mgmtworker"

# these must all be exported as part of the start operation. they will not persist, so we should use the new agent
# don't forget to change all localhosts to the relevant ips
export MGMTWORKER_VIRTUALENV_DIR="${MGMTWORKER_HOME}/env"
export CELERY_WORK_DIR="${MGMTWORKER_HOME}/work"
export CELERY_LOG_DIR="/var/log/cloudify/mgmtworker"
export MGMTWORKER_RIEMANN_POLICY_DIR="/opt/riemann"

# Set broker port for rabbit
export BROKER_PORT_SSL="5671"
export BROKER_PORT_NO_SSL="5672"
export RABBITMQ_SSL_ENABLED="$(ctx -j node properties rabbitmq_ssl_enabled)"
export RABBITMQ_CERT_PUBLIC="$(ctx node properties rabbitmq_cert_public)"

ctx instance runtime_properties rabbitmq_endpoint_ip "$(get_rabbitmq_endpoint_ip)"
ctx instance runtime_properties mgmtworker_user ${MGMTWORKER_USER}
ctx instance runtime_properties mgmtworker_group ${MGMTWORKER_GROUP}

# Fix possible injections in json of rabbit credentials
# See json.org for string spec
for credential in rabbitmq_username rabbitmq_password; do
    # We will not escape newlines or other control characters, we will accept them breaking
    # things noisily, e.g. on newlines and backspaces.
    current_cred="$(ctx node properties ${credential} | sed 's/"/\\"/' | sed 's/\\/\\\\/' | sed s-/-\\/- | sed 's/\t/\\t/')"
    ctx instance runtime_properties ${credential} "${current_cred}"
done

# Make the ssl enabled flag work with json (boolean in lower case)
broker_ssl_enabled="$(echo ${RABBITMQ_SSL_ENABLED} | tr '[:upper:]' '[:lower:]')"
ctx instance runtime_properties rabbitmq_ssl_enabled "${broker_ssl_enabled}"

ctx logger info "Installing Management Worker..."
set_selinux_permissive

copy_notice "mgmtworker"
create_dir ${MGMTWORKER_HOME}
create_dir ${MGMTWORKER_HOME}/config
create_dir ${CELERY_LOG_DIR}
create_dir ${CELERY_WORK_DIR}

create_service_user ${MGMTWORKER_USER} ${MGMTWORKER_HOME} /bin/bash

# This directory is populated when deployments are created- counterintuitively it does need to live here rather than the riemann component
create_dir ${MGMTWORKER_RIEMANN_POLICY_DIR}
set_directory_tree_ownership ${MGMTWORKER_USER} ${MGMTWORKER_GROUP} ${MGMTWORKER_RIEMANN_POLICY_DIR}

# this create the MGMTWORKER_VIRTUALENV_DIR and installs the relevant modules into it.
yum_install ${MANAGEMENT_WORKER_RPM_SOURCE_URL}

# this allows to upgrade modules if necessary.
ctx logger info "Installing Optional Management Worker Modules..."
[ -z ${MANAGEMENT_WORKER_RPM_SOURCE_URL} ] && install_module "celery==${CELERY_VERSION}" ${MGMTWORKER_VIRTUALENV_DIR}
[ -z ${REST_CLIENT_SOURCE_URL} ] || install_module ${REST_CLIENT_SOURCE_URL} ${MGMTWORKER_VIRTUALENV_DIR}
[ -z ${PLUGINS_COMMON_SOURCE_URL} ] || install_module ${PLUGINS_COMMON_SOURCE_URL} ${MGMTWORKER_VIRTUALENV_DIR}
[ -z ${SCRIPT_PLUGIN_SOURCE_URL} ] || install_module ${SCRIPT_PLUGIN_SOURCE_URL} ${MGMTWORKER_VIRTUALENV_DIR}
[ -z ${AGENT_SOURCE_URL} ] || install_module ${AGENT_SOURCE_URL} ${MGMTWORKER_VIRTUALENV_DIR}

# Add certificate and select port, as applicable
if [[ "${RABBITMQ_SSL_ENABLED}" == 'true' ]]; then
  BROKER_CERT_PATH="${MGMTWORKER_HOME}/amqp_pub.pem"
  deploy_ssl_certificate public "${BROKER_CERT_PATH}" "root" "${RABBITMQ_CERT_PUBLIC}"
  ctx instance runtime_properties broker_cert_path "${BROKER_CERT_PATH}"
  # Use SSL port
  ctx instance runtime_properties broker_port ${BROKER_PORT_SSL}
else
  # No SSL, don't use SSL port
  ctx instance runtime_properties broker_port ${BROKER_PORT_NO_SSL}
  if [[ -n "${RABBITMQ_CERT_PUBLIC}" ]]; then
    ctx logger warn "Broker SSL cert supplied but SSL not enabled (broker_ssl_enabled is False)."
  fi
fi

if [ ! -z ${REST_SERVICE_SOURCE_URL} ]; then
    ctx logger info "Downloading cloudify-manager Repository..."
    manager_repo=$(download_cloudify_resource ${REST_SERVICE_SOURCE_URL})
    ctx logger info "Extracting Manager Repository..."
    extract_github_archive_to_tmp ${manager_repo}

    ctx logger info "Installing Management Worker Plugins..."
    # shouldn't we extract the riemann-controller and workflows modules to their own repos?
    install_module "/tmp/plugins/riemann-controller" ${MGMTWORKER_VIRTUALENV_DIR}
    install_module "/tmp/workflows" ${MGMTWORKER_VIRTUALENV_DIR}
fi

ctx logger info "Configuring Management worker..."
# Deploy the broker configuration
# TODO: This will break interestingly if MGMTWORKER_VIRTUALENV_DIR is empty. Some sort of check for that would be sensible.
for python_path in ${MGMTWORKER_VIRTUALENV_DIR}/lib/python*; do
    BROKER_CONF_PATH="${CELERY_WORK_DIR}/broker_config.json"
    deploy_blueprint_resource "${CONFIG_REL_PATH}/broker_config.json" "${BROKER_CONF_PATH}"
    # The config contains credentials, do not let the world read it
    chmod 440 "${BROKER_CONF_PATH}"
done

# Copy or move key files to appropriate locations
if sudo test -f /root/.ssh/agent_key.pem; then
    # We have to copy this at the moment as we still depend on it being in that location for something in non simple-manager bootstrapping
    sudo cp /root/.ssh/agent_key.pem /opt/mgmtworker
else
    # If the key file wasn't where we expected then we're probably running a simple-manager-blueprint
    # If this fails, the management worker wouldn't be able to ssh into any compute nodes, so failing is acceptable
    # Using this ugly approach because tilde expansion isn't working here. This should be fixed when we standardise
    # key locations.
    sudo cp ${SSH_KEY_FILE/\~/\/home\/${AGENT_USER}} /opt/mgmtworker/agent_key.pem
fi

# Set ownership
set_directory_tree_ownership ${MGMTWORKER_USER} ${MGMTWORKER_GROUP} ${MGMTWORKER_HOME}
set_directory_tree_ownership ${MGMTWORKER_USER} ${MGMTWORKER_GROUP} ${MGMTWORKER_VIRTUALENV_DIR}
set_directory_tree_ownership ${MGMTWORKER_USER} ${MGMTWORKER_GROUP} ${CELERY_WORK_DIR}
set_directory_tree_ownership ${MGMTWORKER_USER} ${MGMTWORKER_GROUP} ${CELERY_LOG_DIR}

# Management worker has to create services
# TODO: It would be better if we made a specific script and allowed sudo only for that script to allow the services to be created.
#       This requires modifications to the agent as well, and may require modification to the agent installer.
allow_sudo_for_user ${MGMTWORKER_USER}

configure_systemd_service "mgmtworker"

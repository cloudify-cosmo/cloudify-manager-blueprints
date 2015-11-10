#!/bin/bash -e

. $(ctx download-resource "components/utils")


CONFIG_REL_PATH="components/restservice/config"
REST_RESOURCES_REL_PATH="resources/rest"

# Set broker port for rabbit
BROKER_PORT_SSL=5671
BROKER_PORT_NO_SSL=5672

export REST_SERVICE_RPM_SOURCE_URL=$(ctx node properties rest_service_rpm_source_url)
export DSL_PARSER_SOURCE_URL=$(ctx node properties dsl_parser_module_source_url)
export REST_CLIENT_SOURCE_URL=$(ctx node properties rest_client_module_source_url)
export SECUREST_SOURCE_URL=$(ctx node properties securest_module_source_url)
export REST_SERVICE_SOURCE_URL=$(ctx node properties rest_service_module_source_url)
export PLUGINS_COMMON_SOURCE_URL=$(ctx node properties plugins_common_module_source_url)
export SCRIPT_PLUGIN_SOURCE_URL=$(ctx node properties script_plugin_module_source_url)
export AGENT_SOURCE_URL=$(ctx node properties agent_module_source_url)

# injected as an input to the script
ctx instance runtime_properties es_endpoint_ip ${ES_ENDPOINT_IP}

ctx instance runtime_properties rabbitmq_endpoint_ip "$(get_rabbitmq_endpoint_ip)"

export RABBITMQ_SSL_ENABLED="$(ctx -j node properties rabbitmq_ssl_enabled)"
export RABBITMQ_CERT_PUBLIC="$(ctx node properties rabbitmq_cert_public)"

# TODO: change to /opt/cloudify-rest-service
export REST_SERVICE_HOME="/opt/manager"
export MANAGER_RESOURCES_HOME="/opt/manager/resources"
export RESTSERVICE_VIRTUALENV="${REST_SERVICE_HOME}/env"
# guni.conf currently contains localhost for all endpoints. We need to change that.
# Also, MANAGER_REST_CONFIG_PATH is mandatory since the manager's code reads this env var. it should be renamed to REST_SERVICE_CONFIG_PATH.
export MANAGER_REST_CONFIG_PATH="${REST_SERVICE_HOME}/cloudify-rest.conf"
export REST_SERVICE_CONFIG_PATH="${REST_SERVICE_HOME}/cloudify-rest.conf"
export MANAGER_REST_SECURITY_CONFIG_PATH="${REST_SERVICE_HOME}/rest-security.conf"
export REST_SERVICE_LOG_PATH="/var/log/cloudify/rest"

ctx logger info "Installing REST Service..."
set_selinux_permissive

copy_notice "restservice"
create_dir ${REST_SERVICE_HOME}
create_dir ${REST_SERVICE_LOG_PATH}
create_dir ${MANAGER_RESOURCES_HOME}

# Add certificate and select port, as applicable
if [[ "${RABBITMQ_SSL_ENABLED}" == 'true' ]]; then
  BROKER_CERT_PATH="${REST_SERVICE_HOME}/amqp_pub.pem"
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

# this create the RESTSERVICE_VIRTUALENV and installs the relevant modules into it.
yum_install ${REST_SERVICE_RPM_SOURCE_URL}

# link dbus-python-1.1.1-9.el7.x86_64 to the venv (module in pypi is very old)
if [ -d "/usr/lib64/python2.7/site-packages/dbus" ]; then
  sudo ln -sf /usr/lib64/python2.7/site-packages/dbus "${RESTSERVICE_VIRTUALENV}/lib64/python2.7/site-packages/dbus"
  sudo ln -sf /usr/lib64/python2.7/site-packages/_dbus_*.so "${RESTSERVICE_VIRTUALENV}/lib64/python2.7/site-packages/"
fi

# this allows to upgrade modules if necessary.
ctx logger info "Installing Optional REST Service Modules..."
[ -z ${DSL_PARSER_SOURCE_URL} ] || install_module ${DSL_PARSER_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${REST_CLIENT_SOURCE_URL} ] || install_module ${REST_CLIENT_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${SECUREST_SOURCE_URL} ] || install_module ${SECUREST_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${PLUGINS_COMMON_SOURCE_URL} ] || install_module ${PLUGINS_COMMON_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${SCRIPT_PLUGIN_SOURCE_URL} ] || install_module ${SCRIPT_PLUGIN_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${AGENT_SOURCE_URL} ] || install_module ${AGENT_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}

if [ ! -z ${REST_SERVICE_SOURCE_URL} ]; then
    manager_repo=$(download_cloudify_resource ${REST_SERVICE_SOURCE_URL})
    ctx logger info "Extracting Manager Resources to ${MANAGER_RESOURCES_HOME}..."
    extract_github_archive_to_tmp ${manager_repo}
    install_module "/tmp/rest-service" ${RESTSERVICE_VIRTUALENV}
    ctx logger info "Deploying Required Manager Resources..."
    sudo cp -R "/tmp/resources/rest-service/cloudify/" "${MANAGER_RESOURCES_HOME}"
fi

ctx logger info "Copying role configuration files..."
deploy_blueprint_resource "${REST_RESOURCES_REL_PATH}/roles_config.yaml" "${REST_SERVICE_HOME}/roles_config.yaml"

deploy_logrotate_config "restservice"

ctx logger info "Deploying REST Service Configuration file..."
# rest service ports are set as runtime properties in nginx/scripts/create.sh
deploy_blueprint_resource "${CONFIG_REL_PATH}/cloudify-rest.conf" "${REST_SERVICE_HOME}/cloudify-rest.conf"

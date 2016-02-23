#!/bin/bash -e

. $(ctx download-resource "components/utils")

CONFIG_REL_PATH="components/nginx/config"

export NGINX_SOURCE_URL=$(ctx node properties nginx_rpm_source_url)
export REST_SERVICE_SOURCE_URL=$(ctx node properties rest_service_module_source_url)

export NGINX_LOG_PATH="/var/log/cloudify/nginx"
export MANAGER_RESOURCES_HOME="/opt/manager/resources"
export MANAGER_AGENTS_PATH="${MANAGER_RESOURCES_HOME}/packages/agents"
export MANAGER_SCRIPTS_PATH="${MANAGER_RESOURCES_HOME}/packages/scripts"
export MANAGER_TEMPLATES_PATH="${MANAGER_RESOURCES_HOME}/packages/templates"
NGINX_UNIT_OVERRIDE="/etc/systemd/system/nginx.service.d"

# this is propagated to the agent retrieval script later on so that it's not defined twice.
ctx instance runtime_properties agent_packages_path "${MANAGER_AGENTS_PATH}"

# TODO can we use static (not runtime) attributes for some of these? how to set them?
ctx instance runtime_properties default_rest_service_port "8100"

ctx logger info "Installing Nginx..."
set_selinux_permissive

copy_notice "nginx"
create_dir ${NGINX_LOG_PATH}
create_dir ${MANAGER_RESOURCES_HOME}

create_dir ${MANAGER_AGENTS_PATH}
create_dir ${MANAGER_SCRIPTS_PATH}
create_dir ${MANAGER_TEMPLATES_PATH}

create_dir ${NGINX_UNIT_OVERRIDE}

yum_install ${NGINX_SOURCE_URL}

ctx logger info "Creating systemd unit override..."
deploy_blueprint_resource "${CONFIG_REL_PATH}/restart.conf" "${NGINX_UNIT_OVERRIDE}/restart.conf"

deploy_logrotate_config "nginx"

clean_var_log_dir nginx
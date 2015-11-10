#!/bin/bash -e

. $(ctx download-resource "components/utils")


CONFIG_REL_PATH="components/riemann/config"

export LANGOHR_SOURCE_URL=$(ctx node properties langohr_jar_source_url)
export DAEMONIZE_SOURCE_URL=$(ctx node properties daemonize_rpm_source_url)
export RIEMANN_SOURCE_URL=$(ctx node properties riemann_rpm_source_url)
# Needed for Riemann's config
export CLOUDIFY_RESOURCES_URL=$(ctx node properties cloudify_resources_url)

export RIEMANN_CONFIG_PATH="/etc/riemann"
export RIEMANN_LOG_PATH="/var/log/cloudify/riemann"
export LANGOHR_HOME="/opt/lib"
export EXTRA_CLASSPATH="${LANGOHR_HOME}/langohr.jar"

export RABBITMQ_USERNAME="$(ctx node properties rabbitmq_username)"
export RABBITMQ_PASSWORD="$(ctx node properties rabbitmq_password)"

# Confirm username and password have been supplied for broker before continuing
# Components other than logstash and riemann have this handled in code already
# Note that these are not directly used in this script, but are used by the deployed resources, hence the check here.
if [[ -z "${RABBITMQ_USERNAME}" ]] ||
   [[ -z "${RABBITMQ_PASSWORD}" ]]; then
  sys_error "Both rabbitmq_username and rabbitmq_password must be supplied and at least 1 character long in the manager blueprint inputs."
fi

ctx instance runtime_properties rabbitmq_endpoint_ip "$(get_rabbitmq_endpoint_ip)"

ctx logger info "Installing Riemann..."
set_selinux_permissive

copy_notice "riemann"
create_dir ${RIEMANN_LOG_PATH}
create_dir ${LANGOHR_HOME}
create_dir ${RIEMANN_CONFIG_PATH}
create_dir ${RIEMANN_CONFIG_PATH}/conf.d

langohr=$(download_cloudify_resource ${LANGOHR_SOURCE_URL})
sudo cp ${langohr} ${EXTRA_CLASSPATH}
ctx logger info "Applying Langohr permissions..."
sudo chmod 644 ${EXTRA_CLASSPATH}
ctx logger info "Installing Daemonize..."
yum_install ${DAEMONIZE_SOURCE_URL}
yum_install ${RIEMANN_SOURCE_URL}

deploy_logrotate_config "riemann"

ctx logger info "Downloading cloudify-manager Repository..."
manager_repo=$(download_cloudify_resource ${CLOUDIFY_RESOURCES_URL})
ctx logger info "Extracting Manager Repository..."
extract_github_archive_to_tmp ${manager_repo}
ctx logger info "Deploying Riemann manager.config..."
sudo mv "/tmp/plugins/riemann-controller/riemann_controller/resources/manager.config" "${RIEMANN_CONFIG_PATH}/conf.d/manager.config"

ctx logger info "Deploying Riemann conf..."
deploy_blueprint_resource "${CONFIG_REL_PATH}/main.clj" "${RIEMANN_CONFIG_PATH}/main.clj"

# our riemann configuration will (by default) try to read these environment variables. If they don't exist, it will assume
# that they're found at "localhost"
# export MANAGEMENT_IP=""
# export RABBITMQ_HOST=""

# we inject the management_ip for both of these to Riemann's systemd config. These should be potentially different
# if the manager and rabbitmq are running on different hosts.
configure_systemd_service "riemann"

clean_var_log_dir riemann

#!/bin/bash -e
. $(ctx download-resource "components/utils")

ctx logger info "Deploying Riemann conf..."
CONFIG_REL_PATH="components/riemann/config"
export RIEMANN_CONFIG_PATH="/etc/riemann"

ctx logger info "Deploying Riemann manager.config..."
sudo mv "/tmp/plugins/riemann-controller/riemann_controller/resources/manager.config" "${RIEMANN_CONFIG_PATH}/conf.d/manager.config"

deploy_blueprint_resource "${CONFIG_REL_PATH}/main.clj" "${RIEMANN_CONFIG_PATH}/main.clj"

# our riemann configuration will (by default) try to read these environment variables. If they don't exist, it will assume
# that they're found at "localhost"
# export MANAGEMENT_IP=""
# export RABBITMQ_HOST=""

# we inject the management_ip for both of these to Riemann's systemd config. These should be potentially different
# if the manager and rabbitmq are running on different hosts.
configure_systemd_service "riemann"

clean_var_log_dir riemann
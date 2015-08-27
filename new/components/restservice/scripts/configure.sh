#!/bin/bash -e
. $(ctx download-resource "components/utils")

CONFIG_REL_PATH="components/restservice/config"
REST_SERVICE_HOME="/opt/manager"

ctx logger info "Deploying REST Security configuration file..."
sec_settings=$(ctx -j target node properties security)
echo $sec_settings | sudo tee "${REST_SERVICE_HOME}/rest-security.conf"
configure_systemd_service "restservice"
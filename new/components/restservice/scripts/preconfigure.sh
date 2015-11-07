#!/bin/bash -e
. $(ctx download-resource "components/utils")

CONFIG_REL_PATH="components/restservice/config"
REST_SERVICE_HOME="/opt/manager"

export SELINUX_ENFORCING="$(ctx -j source node properties selinux_enforcing)"

ctx logger info "Deploying REST Security configuration file..."
sec_settings=$(ctx -j target node properties security)
# TODO: do not print to stdout
echo $sec_settings | sudo tee "${REST_SERVICE_HOME}/rest-security.conf"
configure_systemd_service "restservice"

if [[ "${SELINUX_ENFORCING}" == 'true' ]]; then
  apply_selinux_policy restservice "${CONFIG_REL_PATH}/selinux"

  fix_selinux_file_contexts /usr/lib/systemd/system/cloudify-restservice.service
  fix_selinux_file_contexts /opt/manager
  fix_selinux_file_contexts /var/log/cloudify/rest

  allow_selinux_port_tcp http_port_t 9200
  allow_selinux_port_tcp http_port_t 8100
  allow_selinux_port_tcp http_port_t 5672
  allow_selinux_port_tcp http_port_t 5671
fi

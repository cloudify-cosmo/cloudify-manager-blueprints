#!/bin/bash -e

. $(ctx download-resource "components/utils")


CONFIG_REL_PATH="components/logstash/config"
LOGSTASH_UNIT_OVERRIDE="/etc/systemd/system/logstash.service.d"

export LOGSTASH_SOURCE_URL=$(ctx node properties logstash_rpm_source_url)

export RABBITMQ_USERNAME="$(ctx node properties rabbitmq_username)"
export RABBITMQ_PASSWORD="$(ctx node properties rabbitmq_password)"

export RABBITMQ_ENDPOINT_IP="$(ctx node properties rabbitmq_endpoint_ip)"

# injected as an input to the script
ctx instance runtime_properties es_endpoint_ip ${ES_ENDPOINT_IP}

ctx instance runtime_properties rabbitmq_endpoint_ip "$(get_rabbitmq_endpoint_ip)"

# export LOGSTASH_HOME="/opt/logstash"
export LOGSTASH_LOG_PATH="/var/log/cloudify/logstash"
export LOGSTASH_CONF_PATH="/etc/logstash/conf.d"

# Confirm username and password have been supplied for broker before continuing
# Components other than logstash and riemann have this handled in code already
# Note that these are not directly used in this script, but are used by the deployed resources, hence the check here.
if [[ -z "${RABBITMQ_USERNAME}" ]] ||
   [[ -z "${RABBITMQ_PASSWORD}" ]]; then
  sys_error "Both rabbitmq_username and rabbitmq_password must be supplied and at least 1 character long in the manager blueprint inputs."
fi

ctx logger info "Installing Logstash..."
set_selinux_permissive

copy_notice "logstash"

yum_install ${LOGSTASH_SOURCE_URL}

create_dir ${LOGSTASH_LOG_PATH}
sudo chown -R logstash.logstash ${LOGSTASH_LOG_PATH}


ctx logger info "Creating systemd unit override..."
create_dir ${LOGSTASH_UNIT_OVERRIDE}
deploy_blueprint_resource "${CONFIG_REL_PATH}/restart.conf" "${LOGSTASH_UNIT_OVERRIDE}/restart.conf"

ctx logger info "Deploying Logstash conf..."
deploy_blueprint_resource "${CONFIG_REL_PATH}/logstash.conf" "${LOGSTASH_CONF_PATH}/logstash.conf"

ctx logger info "Deploying Logstash sysconfig..."
deploy_blueprint_resource "${CONFIG_REL_PATH}/logstash" "/etc/sysconfig/logstash"

deploy_logrotate_config "logstash"

# sudo systemctl enable logstash.service
sudo /sbin/chkconfig logstash on

clean_var_log_dir "logstash"

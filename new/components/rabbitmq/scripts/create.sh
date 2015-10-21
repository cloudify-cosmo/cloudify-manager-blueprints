#!/bin/bash -e

. $(ctx download-resource "components/utils")

CONFIG_REL_PATH="components/rabbitmq/config"

export ERLANG_SOURCE_URL=$(ctx node properties erlang_rpm_source_url)
export RABBITMQ_SOURCE_URL=$(ctx node properties rabbitmq_rpm_source_url)
export RABBITMQ_FD_LIMIT=$(ctx node properties rabbitmq_fd_limit)

export RABBITMQ_LOG_PATH="/var/log/cloudify/rabbitmq"

export SELINUX_ENFORCING="$(ctx -j node properties selinux_enforcing)"

ctx logger info "Installing RabbitMQ..."

copy_notice "rabbitmq"
create_dir "${RABBITMQ_LOG_PATH}"

export RABBITMQ_USERNAME="$(ctx node properties rabbitmq_username)"
export RABBITMQ_PASSWORD="$(ctx node properties rabbitmq_password)"
export RABBITMQ_SSL_ENABLED="$(ctx -j node properties rabbitmq_ssl_enabled)"
export RABBITMQ_CERT_PUBLIC="$(ctx node properties rabbitmq_cert_public)"
export RABBITMQ_CERT_PRIVATE="$(ctx node properties rabbitmq_cert_private)"

yum_install ${ERLANG_SOURCE_URL}
yum_install ${RABBITMQ_SOURCE_URL}

deploy_logrotate_config "rabbitmq"

# Creating rabbitmq systemd stop script
deploy_blueprint_resource "${CONFIG_REL_PATH}/kill-rabbit" "/usr/local/bin/kill-rabbit"
sudo chmod 500 /usr/local/bin/kill-rabbit

configure_systemd_service "rabbitmq"

ctx logger info "Configuring File Descriptors Limit..."
deploy_blueprint_resource "${CONFIG_REL_PATH}/rabbitmq_ulimit.conf" "/etc/security/limits.d/rabbitmq.conf"
sudo systemctl daemon-reload

ctx logger info "Chowning RabbitMQ logs path..."
sudo chown rabbitmq:rabbitmq ${RABBITMQ_LOG_PATH}

# Deploy certificates if both have been provided. Complain loudly if one has been provided and the other hasn't.
if [[ "${RABBITMQ_SSL_ENABLED}" == 'true' ]]; then
  if [[ -n "${RABBITMQ_CERT_PRIVATE}" ]]; then
    if [[ -n "${RABBITMQ_CERT_PUBLIC}" ]]; then
      deploy_ssl_certificate private "/etc/rabbitmq/rabbit-priv.pem" "rabbitmq" "${RABBITMQ_CERT_PRIVATE}"
      deploy_ssl_certificate public "/etc/rabbitmq/rabbit-pub.pem" "rabbitmq" "${RABBITMQ_CERT_PUBLIC}"
      # Configure for SSL
      deploy_blueprint_resource "${CONFIG_REL_PATH}/rabbitmq.config-ssl" "/etc/rabbitmq/rabbitmq.config"
    else
      sys_error "When providing a private certificate for rabbitmq, the public certificate must also be supplied."
    fi
  else
    if [[ -n "${RABBITMQ_CERT_PUBLIC}" ]]; then
      sys_error "When providing a public certificate for rabbitmq, the private certificate must also be supplied."
    fi
  fi
else
  # Configure for no SSL
  deploy_blueprint_resource "${CONFIG_REL_PATH}/rabbitmq.config-nossl" "/etc/rabbitmq/rabbitmq.config"
  if [[ -n "${RABBITMQ_CERT_PRIVATE}" ]] || [[ -n "${RABBITMQ_CERT_PUBLIC}" ]]; then
    ctx logger warn "Broker SSL cert supplied but SSL not enabled (broker_ssl_enabled is False)."
  fi
fi

if [[ "${SELINUX_ENFORCING}" == 'true' ]]; then
  apply_selinux_policy rabbitmq "${CONFIG_REL_PATH}/selinux"

  fix_selinux_file_contexts /etc/rabbitmq
  fix_selinux_file_contexts /var/log/cloudify/rabbitmq
fi

ctx logger info "Starting RabbitMQ Server in Daemonized mode..."
sudo systemctl start cloudify-rabbitmq.service

ctx logger info "Enabling RabbitMQ Plugins..."
# Occasional timing issues with rabbitmq starting have resulted in failures when first trying to enable plugins
run_command_with_retries "sudo rabbitmq-plugins enable rabbitmq_management"
run_command_with_retries "sudo rabbitmq-plugins enable rabbitmq_tracing"

ctx logger info "Disabling RabbitMQ guest user"
run_command_with_retries "sudo rabbitmqctl clear_permissions guest"
run_command_with_retries "sudo rabbitmqctl delete_user guest"

ctx logger info "Creating new RabbitMQ user and setting permissions"
run_command_with_retries sudo rabbitmqctl add_user ${RABBITMQ_USERNAME} ${RABBITMQ_PASSWORD}
run_noglob_command_with_retries sudo rabbitmqctl set_permissions ${RABBITMQ_USERNAME} '.*' '.*' '.*'

ctx logger info "Stopping RabbitMQ Service..."
# Systemd service stopping has been returning non zero when successful
set +e
sudo systemctl stop cloudify-rabbitmq.service
if [[ $? -eq 143 ]]; then
        if [[ $? -ne 0 ]]; then
                exit $?
        fi
fi

clean_var_log_dir rabbitmq


#!/bin/bash -e

. $(ctx download-resource "components/utils")

export AMQPINFLUX_RPM_SOURCE_URL=$(ctx node properties amqpinflux_rpm_source_url)
export AMQPINFLUX_SOURCE_URL=$(ctx node properties amqpinflux_module_source_url)

# injected as an input to the script
ctx instance runtime_properties influxdb_endpoint_ip ${INFLUXDB_ENDPOINT_IP}

ctx instance runtime_properties rabbitmq_endpoint_ip "$(get_rabbitmq_endpoint_ip)"

export AMQPINFLUX_HOME="/opt/amqpinflux"
export AMQPINFLUX_USER="amqpinflux"
export AMQPINFLUX_GROUP="amqpinflux"
export AMQPINFLUX_VIRTUALENV_DIR="${AMQPINFLUX_HOME}/env"

export RABBITMQ_CERT_ENABLED="$(ctx -j node properties rabbitmq_ssl_enabled)"
export RABBITMQ_CERT_PUBLIC="$(ctx node properties rabbitmq_cert_public)"

ctx logger info "Installing AQMPInflux..."
set_selinux_permissive

copy_notice "amqpinflux"
create_dir "${AMQPINFLUX_HOME}"

# this creates the AMQPINFLUX_VIRTUALENV_DIR and installs the module into it.
yum_install ${AMQPINFLUX_RPM_SOURCE_URL}
# this allows to upgrade amqpinflux if necessary.
[ -z "${AMQPINFLUX_SOURCE_URL}" ] || install_module ${AMQPINFLUX_SOURCE_URL} "${AMQPINFLUX_VIRTUALENV_DIR}"

create_service_user ${AMQPINFLUX_USER} ${AMQPINFLUX_HOME}

if [[ "${RABBITMQ_CERT_ENABLED}" == 'true' ]]; then
  BROKER_CERT_PATH="${AMQPINFLUX_HOME}/amqp_pub.pem"
  # If no certificate was supplied, the deploy function will raise an error
  deploy_ssl_certificate public "${BROKER_CERT_PATH}" "${AMQPINFLUX_GROUP}" "${RABBITMQ_CERT_PUBLIC}"
  ctx instance runtime_properties broker_cert_path "${BROKER_CERT_PATH}"
else
  if [[ -n "${RABBITMQ_CERT_PUBLIC}" ]]; then
    ctx logger warn "Broker SSL cert supplied but SSL not enabled (broker_ssl_enabled is False)."
  fi
fi

ctx logger info "Fixing permissions..."
sudo chown -R "${AMQPINFLUX_USER}:${AMQPINFLUX_GROUP}" "${AMQPINFLUX_HOME}"

configure_systemd_service "amqpinflux"

#!/bin/bash -e

. $(ctx download-resource "components/utils")


CONFIG_REL_PATH="components/riemann/config"

export LANGOHR_SOURCE_URL=$(ctx node properties langohr_jar_source_url)  # (e.g. "https://s3-eu-west-1.amazonaws.com/gigaspaces-repository-eu/langohr/2.11.0/langohr.jar")
export DAEMONIZE_SOURCE_URL=$(ctx node properties daemonize_rpm_source_url)  # (e.g. "https://forensics.cert.org/centos/cert/7/x86_64/daemonize-1.7.3-7.el7.x86_64.rpm")
export RIEMANN_SOURCE_URL=$(ctx node properties riemann_rpm_source_url)  # (e.g. "https://aphyr.com/riemann/riemann-0.2.6-1.noarch.rpm")
export RIEMANN_MASTER_CONFIG_URL=$(ctx node properties riemann_master_config_url)

export RIEMANN_CONFIG_PATH="/etc/riemann"
export RIEMANN_LOG_PATH="/var/log/cloudify/riemann"
export LANGOHR_HOME="/opt/lib"
export EXTRA_CLASSPATH="${LANGOHR_HOME}/langohr.jar"

# our riemann configuration will (by default) try to read these environment variables. If they don't exist, it will assume
# that they're found at "localhost"
# export MANAGEMENT_IP=""
# export RABBITMQ_HOST=""


ctx logger info "Installing Riemann..."

copy_notice "riemann"
create_dir ${RIEMANN_LOG_PATH}
create_dir ${LANGOHR_HOME}
create_dir ${RIEMANN_CONFIG_PATH}
create_dir ${RIEMANN_CONFIG_PATH}/conf.d

langohr=$(download_file ${LANGOHR_SOURCE_URL})
sudo mv ${langohr} ${EXTRA_CLASSPATH}
ctx logger info "Applying Langohr permissions..."
sudo chmod 644 ${EXTRA_CLASSPATH}
ctx logger info "Installing Daemonize..."
yum_install ${DAEMONIZE_SOURCE_URL}
yum_install ${RIEMANN_SOURCE_URL}

ctx logger info "Configuring logrotate..."
lconf="/etc/logrotate.d/riemann"

cat << EOF | sudo tee $lconf > /dev/null
$RIEMANN_LOG_PATH/*.log {
        daily
        rotate 7
        copytruncate
        compress
        delaycompress
        missingok
        notifempty
}
EOF

sudo chmod 644 $lconf

ctx logger info "Deploying Riemann manager.config..."
manager_config=$(download_file ${RIEMANN_MASTER_CONFIG_URL})
sudo mv ${manager_config} ${RIEMANN_CONFIG_PATH}/conf.d/manager.config

ctx logger info "Deploying Riemann conf..."
deploy_file "${CONFIG_REL_PATH}/main.clj" "${RIEMANN_CONFIG_PATH}/main.clj"

configure_systemd_service "riemann"
#!/bin/bash -e

. $(ctx download-resource "components/utils")


export DSL_PARSER_SOURCE_URL=$(ctx node properties dsl_parser_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-dsl-parser/archive/3.2.tar.gz")
export REST_CLIENT_SOURCE_URL=$(ctx node properties rest_client_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-rest-client/archive/3.2.tar.gz")
export SECUREST_SOURCE_URL=$(ctx node properties securest_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/flask-securest/archive/0.6.tar.gz")
export REST_SERVICE_SOURCE_URL=$(ctx node properties rest_service_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-manager/archive/3.2.tar.gz")

# TODO: change to /opt/cloudify-rest-service
export REST_SERVICE_HOME="/opt/manager"
export REST_SERVICE_VIRTUALENV="${REST_SERVICE_HOME}/env"
# guni.conf currently contains localhost for all endpoints. We need to change that.
# Also, MANAGER_REST_CONFIG_PATH is mandatory since the manager's code reads this env var. it should be renamed to REST_SERVICE_CONFIG_PATH.
export MANAGER_REST_CONFIG_PATH="${REST_SERVICE_HOME}/guni.conf"
export REST_SERVICE_CONFIG_PATH="${REST_SERVICE_HOME}/guni.conf"
export REST_SERVICE_LOG_PATH="/var/log/cloudify/rest"


ctx logger info "Installing REST Service..."

copy_notice "restservice"
create_dir ${REST_SERVICE_HOME}
create_dir ${REST_SERVICE_LOG_PATH}

ctx logger info "Creating virtualenv ${REST_SERVICE_VIRTUALENV}..."
create_virtualenv ${REST_SERVICE_VIRTUALENV}

ctx logger info "Installing Required REST Service Modules..."
install_module ${DSL_PARSER_SOURCE_URL} ${REST_SERVICE_VIRTUALENV}
install_module ${REST_CLIENT_SOURCE_URL} ${REST_SERVICE_VIRTUALENV}
install_module ${SECUREST_SOURCE_URL} ${REST_SERVICE_VIRTUALENV}
ctx logger info "Downloading Manager Repository..."
# insecure matters here?
# curl --fail --insecure -L ${REST_SERVICE_SOURCE_URL} --create-dirs -o /tmp/cloudify-manager/manager.tar.gz
manager_repo=$(download_file ${REST_SERVICE_SOURCE_URL})
ctx logger info "Extracting Manager..."
tar -xzf ${manager_repo} --strip-components=1 -C "/tmp"
install_module "/tmp/rest-service" ${REST_SERVICE_VIRTUALENV}

ctx logger info "Configuring logrotate..."
lconf="/etc/logrotate.d/gunicorn"

cat << EOF | sudo tee $lconf > /dev/null
$REST_SERVICE_LOG_PATH/*.log {
        daily
        missingok
        rotate 7
        compress
        delaycompress
        notifempty
        sharedscripts
        postrotate
                [ -f /var/run/gunicorn.pid ] && kill -USR1 \$(cat /var/run/gunicorn.pid)
        endscript
}
EOF

sudo chmod 644 $lconf

ctx logger info "Deploying Gunicorn and REST Service Configuration file..."
guni_conf=$(ctx download-resource "components/restservice/config/guni.conf")
sudo mv ${guni_conf} "${REST_SERVICE_HOME}/guni.conf"

ctx logger info "Deploying Service systemd EnvironmentFile..."
envfile=$(ctx download-resource "components/restservice/config/cloudify-rest")
sudo mv ${envfile} "/etc/sysconfig/cloudify-rest"

ctx logger info "Deploying Service systemd .service file..."
servicefile=$(ctx download-resource "components/restservice/config/cloudify-rest.service")
sudo mv ${servicefile} "/usr/lib/systemd/system/cloudify-rest.service"

ctx logger info "Enabling .service..."
sudo systemctl enable cloudify-rest.service
sudo systemctl daemon-reload
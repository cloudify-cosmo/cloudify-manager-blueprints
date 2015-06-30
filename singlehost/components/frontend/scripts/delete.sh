#!/bin/bash -e

. $(ctx download-resource "components/utils")


export NGINX_SOURCE_URL=$(ctx node properties nginx_rpm_source_url)  # (e.g. "https://dl.dropboxusercontent.com/u/407576/3.2/nginx-1.8.0-1.el7.ngx.x86_64.rpm")

export NGINX_LOG_PATH="/var/log/cloudify/nginx"
export MANAGER_RESOURCES_HOME="/opt/manager/resources"
export SSL_CERTS_ROOT="/root/cloudify"


ctx logger info "Uninstalling Nginx..."

ctx logger info "Disabling Nginx Service..."
sudo systemctl disable nginx.service

remove_notice "frontend"
remove_dir ${NGINX_LOG_PATH}
remove_dir ${MANAGER_RESOURCES_HOME}
remove_dir ${SSL_CERTS_ROOT}

yum_uninstall ${NGINX_SOURCE_URL}

ctx logger info "Removing Files..."
sudo rm "/etc/nginx/conf.d/default.conf"
sudo rm "/etc/nginx/conf.d/rest-location.cloudify"
sudo rm "/etc/logrotate.d/influxdb"
sudo rm "${SSL_CERTS_ROOT}/server.crt"
sudo rm "${SSL_CERTS_ROOT}/server.key"
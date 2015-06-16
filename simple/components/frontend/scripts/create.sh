#!/bin/bash -e

. $(ctx download-resource "components/utils")


export REST_SERVICE_URL=$(ctx node properties rest_service_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-manager/archive/3.2.tar.gz")
export CENTOS7_AGENT_SOURCE_URL=$(ctx node properties centos7_agent_source_url)  # (e.g. "https://dl.dropboxusercontent.com/u/407576/centos-Core-agent.tar.gz")
export REQUIRE_TTY_SOURCE_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-packager/CFY-2596-centos7-agent/package-configuration/centos-agent/centos-agent-disable-requiretty.sh"
export CELERY_CONF_SOURCE_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-packager/CFY-2596-centos7-agent/package-configuration/centos-agent/centos-celeryd-cloudify.conf.template"
export CELERY_INIT_SOURCE_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-packager/CFY-2596-centos7-agent/package-configuration/centos-agent/centos-celeryd-cloudify.init.template"

export NGINX_LOG_PATH="/var/log/cloudify/nginx"
export NGINX_REPO="http://nginx.org/packages/centos/7/noarch/RPMS/nginx-release-centos-7-0.el7.ngx.noarch.rpm"
export MANAGER_RESOURCES_HOME="/opt/manager/resources"
export MANAGER_AGENTS_PATH="${MANAGER_RESOURCES_HOME}/packages/agents"
export MANAGER_SCRIPTS_PATH="${MANAGER_RESOURCES_HOME}/packages/scripts"
export MANAGER_TEMPLATES_PATH="${MANAGER_RESOURCES_HOME}/packages/templates"
export SSL_CERTS_ROOT="/root/cloudify"


ctx logger info "Installing Nginx..."

copy_notice "frontend"
create_dir ${NGINX_LOG_PATH}
create_dir ${MANAGER_RESOURCES_HOME}
create_dir "${SSL_CERTS_ROOT}"

create_dir ${MANAGER_AGENTS_PATH}
create_dir ${MANAGER_SCRIPTS_PATH}
create_dir ${MANAGER_TEMPLATES_PATH}

yum_install ${NGINX_REPO}
yum_install nginx

ctx logger info "Copying default.conf file to /etc/nginx/conf.d/default.conf..."
default_conf=$(ctx download-resource "components/frontend/config/default.conf")
sudo mv ${default_conf} "/etc/nginx/conf.d/default.conf"

ctx logger info "Copying rest-location.cloudify file to /etc/nginx/conf.d/rest-location.cloudify..."
cloudify_conf=$(ctx download-resource "components/frontend/config/rest-location.cloudify")
sudo mv ${cloudify_conf} "/etc/nginx/conf.d/rest-location.cloudify"

ctx logger info "Copying SSL Certs..."
crt=$(ctx download-resource "components/frontend/config/ssl/server.crt")
sudo mv ${crt} "${SSL_CERTS_ROOT}/"
key=$(ctx download-resource "components/frontend/config/ssl/server.key")
sudo mv ${key} "${SSL_CERTS_ROOT}/"

ctx logger info "Deploying Required Manager Resources..."
manager_repo=$(download_file ${REST_SERVICE_SOURCE_URL})
ctx logger info "Extracting Manager Resources to ${MANAGER_RESOURCES_HOME}..."
tar -xzf ${manager_repo} --strip-components=1 -C "/tmp/cloudify-manager/"
sudo cp -R "/tmp/cloudify-manager/resources/rest-service/cloudify/" "${MANAGER_RESOURCES_HOME}"
clean_tmp

ctx logger info "Downloading Centos Agent resources..."
centos_agent=$(download_file ${CENTOS7_AGENT_SOURCE_URL})
sudo mv ${centos_agent} "${MANAGER_AGENTS_PATH}/centos-Core-agent.tar.gz"
require_tty_script=$(download_file ${REQUIRE_TTY_SOURCE_URL})
sudo mv ${require_tty_script} "${MANAGER_SCRIPTS_PATH}/centos-agent-disable-requiretty.sh"
celery_conf=$(download_file ${CELERY_CONF_SOURCE_URL})
sudo mv ${celery_conf} "${MANAGER_TEMPLATES_PATH}/centos-celeryd-cloudify.conf.template"
celery_init=$(download_file ${CELERY_INIT_SOURCE_URL})
sudo mv ${celery_init} "${MANAGER_TEMPLATES_PATH}/centos-celeryd-cloudify.init.template"

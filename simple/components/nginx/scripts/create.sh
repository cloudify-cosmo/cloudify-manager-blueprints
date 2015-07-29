#!/bin/bash -e

. $(ctx download-resource "components/utils")

CONFIG_REL_PATH="components/nginx/config"

export NGINX_SOURCE_URL=$(ctx node properties nginx_rpm_source_url)  # (e.g. "https://dl.dropboxusercontent.com/u/407576/3.2/nginx-1.8.0-1.el7.ngx.x86_64.rpm")
export REST_SERVICE_SOURCE_URL=$(ctx node properties rest_service_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-manager/archive/3.2.tar.gz")

export REQUIRE_TTY_SOURCE_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-packager/CFY-2596-centos7-agent/package-configuration/centos-agent/centos-agent-disable-requiretty.sh"
export CELERY_CONF_SOURCE_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-packager/CFY-2596-centos7-agent/package-configuration/centos-agent/centos-celeryd-cloudify.conf.template"
export CELERY_INIT_SOURCE_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-packager/CFY-2596-centos7-agent/package-configuration/centos-agent/centos-celeryd-cloudify.init.template"


export NGINX_LOG_PATH="/var/log/cloudify/nginx"
# export NGINX_REPO="http://nginx.org/packages/centos/7/noarch/RPMS/nginx-release-centos-7-0.el7.ngx.noarch.rpm"
export MANAGER_RESOURCES_HOME="/opt/manager/resources"
export MANAGER_AGENTS_PATH="${MANAGER_RESOURCES_HOME}/packages/agents"
export MANAGER_SCRIPTS_PATH="${MANAGER_RESOURCES_HOME}/packages/scripts"
export MANAGER_TEMPLATES_PATH="${MANAGER_RESOURCES_HOME}/packages/templates"
export SSL_CERTS_ROOT="/root/cloudify"

# this is propagated to the agent retrieval script later on so that it's not defined twice.
ctx instance runtime_properties agent_packages_path "${MANAGER_AGENTS_PATH}"


ctx logger info "Installing Nginx..."

copy_notice "nginx"
create_dir ${NGINX_LOG_PATH}
create_dir ${MANAGER_RESOURCES_HOME}
create_dir ${SSL_CERTS_ROOT}

create_dir ${MANAGER_AGENTS_PATH}
create_dir ${MANAGER_SCRIPTS_PATH}
create_dir ${MANAGER_TEMPLATES_PATH}

yum_install ${NGINX_SOURCE_URL}

ctx logger info "Deploying Nginx configuration files..."
deploy_file "${CONFIG_REL_PATH}/default.conf" "/etc/nginx/conf.d/default.conf"
deploy_file "${CONFIG_REL_PATH}/rest-location.cloudify" "/etc/nginx/conf.d/rest-location.cloudify"

ctx logger info "Configuring logrotate..."
lconf="/etc/logrotate.d/nginx"

cat << EOF | sudo tee $lconf >/dev/null
$NGINX_LOG_PATH/*.log {
        daily
        missingok
        rotate 7
        compress
        delaycompress
        notifempty
        create 640 nginx adm
        sharedscripts
        postrotate
                [ -f /var/run/nginx.pid ] && kill -USR1 \$(cat /var/run/nginx.pid)
        endscript
}
EOF

sudo chmod 644 $lconf


ctx logger info "Copying SSL Certs..."
deploy_file "${CONFIG_REL_PATH}/ssl/server.crt" "${SSL_CERTS_ROOT}/server.crt"
deploy_file "${CONFIG_REL_PATH}/ssl/server.key" "${SSL_CERTS_ROOT}/server.key"

ctx logger info "Deploying Required Manager Resources..."
manager_repo=$(download_file ${REST_SERVICE_SOURCE_URL})
ctx logger info "Extracting Manager Resources to ${MANAGER_RESOURCES_HOME}..."
tar -xzf ${manager_repo} --strip-components=1 -C "/tmp" >/dev/null
sudo cp -R "/tmp/resources/rest-service/cloudify/" "${MANAGER_RESOURCES_HOME}"


require_tty_script=$(download_file ${REQUIRE_TTY_SOURCE_URL})
sudo cp ${require_tty_script} "${MANAGER_SCRIPTS_PATH}/centos-agent-disable-requiretty.sh"
sudo mv ${require_tty_script} "${MANAGER_SCRIPTS_PATH}/Ubuntu-agent-disable-requiretty.sh"

celery_conf=$(download_file ${CELERY_CONF_SOURCE_URL})
sudo cp ${celery_conf} "${MANAGER_TEMPLATES_PATH}/centos-celeryd-cloudify.conf.template"
sudo mv ${celery_conf} "${MANAGER_TEMPLATES_PATH}/Ubuntu-celeryd-cloudify.conf.template"

celery_init=$(download_file ${CELERY_INIT_SOURCE_URL})
sudo cp ${celery_init} "${MANAGER_TEMPLATES_PATH}/centos-celeryd-cloudify.init.template"
sudo mv ${celery_init} "${MANAGER_TEMPLATES_PATH}/Ubuntu-celeryd-cloudify.init.template"

sudo systemctl enable nginx.service &>/dev/null
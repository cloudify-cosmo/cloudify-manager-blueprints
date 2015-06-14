#!/bin/bash -e

NGINX_LOG_PATH="/var/log/cloudify/nginx"
NGINX_REPO="http://nginx.org/packages/centos/7/noarch/RPMS/nginx-release-centos-7-0.el7.ngx.noarch.rpm"
MANAGER_RESOURCES_HOME="/opt/manager/resources"
# REST_SERVICE_URL=$(ctx node properties rest_service_url)
export REST_SERVICE_VERSION="3.2"
export REST_SERVICE_SOURCE_URL="https://github.com/cloudify-cosmo/cloudify-manager/archive/${REST_SERVICE_VERSION}.tar.gz"
CENTOS7_AGENT_SOURCE_URL="https://dl.dropboxusercontent.com/u/407576/centos-Core-agent.tar.gz"
# CENTOS7_AGENT_SOURCE_URL=$(ctx node properties centos7_agent_source_url)
REQUIRE_TTY_SOURCE_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-packager/CFY-2596-centos7-agent/package-configuration/centos-agent/centos-agent-disable-requiretty.sh"
CELERY_CONF_SOURCE_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-packager/CFY-2596-centos7-agent/package-configuration/centos-agent/centos-celeryd-cloudify.conf.template"
CELERY_INIT_SOURCE_URL="https://raw.githubusercontent.com/cloudify-cosmo/cloudify-packager/CFY-2596-centos7-agent/package-configuration/centos-agent/centos-celeryd-cloudify.init.template"


function import_helpers
{
    if [ ! -e "/tmp/utils" ]; then
        cp components/utils /tmp/utils
        # ctx download-resource "components/utils" '@{"target_path": "/tmp/utils"}'
    fi
    . /tmp/utils
    # required only in current vagrant environment otherwise passed to the vm via the script plugin
    . components/env_vars
}

function main
{
    ctx logger info "Installing Nginx..."

    copy_notice "frontend" && \
    create_dir ${NGINX_LOG_PATH} && \
    create_dir ${MANAGER_RESOURCES_HOME} && \
    create_dir "/root/cloudify" && \

    create_dir "/opt/manager/resources/packages/agents"
    create_dir "/opt/manager/resources/packages/templates"
    create_dir "/opt/manager/resources/packages/scripts"

    install_rpm ${NGINX_REPO} && \
    sudo yum install nginx -y && \

    ctx logger info "Copying default.conf file to /etc/nginx/conf.d/default.conf..."
    sudo cp "components/frontend/config/default.conf" "/tmp/default.conf" && \
    sudo mv "/tmp/default.conf" "/etc/nginx/conf.d/default.conf" && \

    ctx logger info "Copying rest-location.cloudify file to /etc/nginx/conf.d/rest-location.cloudify..."
    sudo cp "components/frontend/config/rest-location.cloudify" "/tmp/rest-location.cloudify" && \
    sudo mv "/tmp/rest-location.cloudify" "/etc/nginx/conf.d/rest-location.cloudify" && \

    ctx logger info "Copying SSL Certs..."
    sudo cp components/frontend/config/ssl/* "/tmp/" && \
    sudo mv /tmp/server.* "/root/cloudify/" && \

    ctx logger info "Deploying Required Manager Resources..."
    curl --fail -L ${REST_SERVICE_SOURCE_URL} --create-dirs -o "/tmp/cloudify-manager/manager.tar.gz" && \
    ctx logger info "Extracting Manager Resources to ${MANAGER_RESOURCES_HOME}..."
    tar -xzf "/tmp/cloudify-manager/manager.tar.gz" --strip-components=1 -C "/tmp/cloudify-manager/" && \
    sudo cp -R "/tmp/cloudify-manager/resources/rest-service/cloudify/" "${MANAGER_RESOURCES_HOME}" && \
    clean_tmp

    ctx logger info "Downloading Centos Agent resources..."
    download_file ${CENTOS7_AGENT_SOURCE_URL} "/tmp/centos-Core-agent.tar.gz"
    sudo mv "/tmp/centos-Core-agent.tar.gz" "/opt/manager/resources/packages/agents/"
    download_file ${REQUIRE_TTY_SOURCE_URL} "/tmp/centos-agent-disable-requiretty.sh"
    sudo mv "/tmp/centos-agent-disable-requiretty.sh" "/opt/manager/resources/packages/scripts/"
    download_file ${CELERY_CONF_SOURCE_URL} "/tmp/centos-celeryd-cloudify.conf.template"
    sudo mv "/tmp/centos-celeryd-cloudify.conf.template" "/opt/manager/resources/packages/templates/"
    download_file ${CELERY_INIT_SOURCE_URL} "/tmp/centos-celeryd-cloudify.init.template"
    sudo mv "/tmp/centos-celeryd-cloudify.init.template" "/opt/manager/resources/packages/templates/"

}

cd /vagrant
import_helpers
main
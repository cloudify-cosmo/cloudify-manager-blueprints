#!/bin/bash -e

. $(ctx download-resource "components/utils")


CONFIG_REL_PATH="components/restservice/config"

export REST_SERVICE_RPM_SOURCE_URL=$(ctx node properties rest_service_rpm_source_url)
export DSL_PARSER_SOURCE_URL=$(ctx node properties dsl_parser_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-dsl-parser/archive/3.2.tar.gz")
export REST_CLIENT_SOURCE_URL=$(ctx node properties rest_client_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-rest-client/archive/3.2.tar.gz")
export SECUREST_SOURCE_URL=$(ctx node properties securest_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/flask-securest/archive/0.6.tar.gz")
export REST_SERVICE_SOURCE_URL=$(ctx node properties rest_service_module_source_url)  # (e.g. "https://github.com/cloudify-cosmo/cloudify-manager/archive/3.2.tar.gz")
export PLUGINS_COMMON_SOURCE_URL=$(ctx node properties plugins_common_module_source_url)
export SCRIPT_PLUGIN_SOURCE_URL=$(ctx node properties script_plugin_module_source_url)
export AGENT_SOURCE_URL=$(ctx node properties agent_module_source_url)

# injected as an input to the script
ctx instance runtime_properties es_endpoint_ip ${ES_ENDPOINT_IP}

# TODO: change to /opt/cloudify-rest-service
export REST_SERVICE_HOME="/opt/manager"
export MANAGER_RESOURCES_HOME="/opt/manager/resources"
export RESTSERVICE_VIRTUALENV="${REST_SERVICE_HOME}/env"
# guni.conf currently contains localhost for all endpoints. We need to change that.
# Also, MANAGER_REST_CONFIG_PATH is mandatory since the manager's code reads this env var. it should be renamed to REST_SERVICE_CONFIG_PATH.
export MANAGER_REST_CONFIG_PATH="${REST_SERVICE_HOME}/cloudify-rest.conf"
export REST_SERVICE_CONFIG_PATH="${REST_SERVICE_HOME}/cloudify-rest.conf"
export MANAGER_REST_SECURITY_CONFIG_PATH="${REST_SERVICE_HOME}/rest-security.conf"
export REST_SERVICE_LOG_PATH="/var/log/cloudify/rest"

ctx logger info "Installing REST Service..."
set_selinux_permissive

copy_notice "restservice"
create_dir ${REST_SERVICE_HOME}
create_dir ${REST_SERVICE_LOG_PATH}
create_dir ${MANAGER_RESOURCES_HOME}

# this create the RESTSERVICE_VIRTUALENV and installs the relevant modules into it.
yum_install ${REST_SERVICE_RPM_SOURCE_URL}

# link dbus-python-1.1.1-9.el7.x86_64 to the venv (module in pypi is very old)
if [ -d "/usr/lib64/python2.7/site-packages/dbus" ]; then
  sudo ln -sf /usr/lib64/python2.7/site-packages/dbus "${RESTSERVICE_VIRTUALENV}/lib64/python2.7/site-packages/dbus"
  sudo ln -sf /usr/lib64/python2.7/site-packages/_dbus_*.so "${RESTSERVICE_VIRTUALENV}/lib64/python2.7/site-packages/"
fi

# this allows to upgrade modules if necessary.
ctx logger info "Installing Optional REST Service Modules..."
[ -z ${DSL_PARSER_SOURCE_URL} ] || install_module ${DSL_PARSER_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${REST_CLIENT_SOURCE_URL} ] || install_module ${REST_CLIENT_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${SECUREST_SOURCE_URL} ] || install_module ${SECUREST_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${PLUGINS_COMMON_SOURCE_URL} ] || install_module ${PLUGINS_COMMON_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${SCRIPT_PLUGIN_SOURCE_URL} ] || install_module ${SCRIPT_PLUGIN_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}
[ -z ${AGENT_SOURCE_URL} ] || install_module ${AGENT_SOURCE_URL} ${RESTSERVICE_VIRTUALENV}

if [ ! -z ${REST_SERVICE_SOURCE_URL} ]; then
    manager_repo=$(download_cloudify_resource ${REST_SERVICE_SOURCE_URL})
    ctx logger info "Extracting Manager Resources to ${MANAGER_RESOURCES_HOME}..."
    tar -xzf ${manager_repo} --strip-components=1 -C "/tmp" >/dev/null
    install_module "/tmp/rest-service" ${RESTSERVICE_VIRTUALENV}
    ctx logger info "Deploying Required Manager Resources..."
    sudo cp -R "/tmp/resources/rest-service/cloudify/" "${MANAGER_RESOURCES_HOME}"
fi


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

ctx logger info "Deploying REST Service Configuration file..."
# rest service ports are set as runtime properties in nginx/scripts/create.sh
deploy_blueprint_resource "${CONFIG_REL_PATH}/cloudify-rest.conf" "${REST_SERVICE_HOME}/cloudify-rest.conf"

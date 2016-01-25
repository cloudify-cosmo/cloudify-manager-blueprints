#!/bin/bash -e

. $(ctx download-resource "components/utils")

CONFIG_REL_PATH="components/nginx/config"
SSL_RESOURCES_REL_PATH="resources/ssl"

export SSL_CERTS_ROOT="/root/cloudify"

# these settings are used by nginx's default.conf to select the relevant configuration
EXTERNAL_REST_PROTOCOL=$(ctx target instance runtime_properties external_rest_protocol)
ctx source instance runtime_properties external_rest_protocol ${EXTERNAL_REST_PROTOCOL}

if [ "${EXTERNAL_REST_PROTOCOL}" = "https" ]; then
    ctx logger info "Copying SSL Certs..."
    create_dir ${SSL_CERTS_ROOT}
    deploy_blueprint_resource "${SSL_RESOURCES_REL_PATH}/server.crt" "${SSL_CERTS_ROOT}/server.crt"
    deploy_blueprint_resource "${SSL_RESOURCES_REL_PATH}/server.key" "${SSL_CERTS_ROOT}/server.key"
fi

INTERNAL_REST_PROTOCOL=$(ctx target instance runtime_properties internal_rest_protocol)
ctx source instance runtime_properties internal_rest_protocol ${INTERNAL_REST_PROTOCOL}

ctx logger info "Deploying Nginx configuration files..."
deploy_blueprint_resource "${CONFIG_REL_PATH}/${EXTERNAL_REST_PROTOCOL}-external-rest-server.cloudify" "/etc/nginx/conf.d/${EXTERNAL_REST_PROTOCOL}-external-rest-server.cloudify"
deploy_blueprint_resource "${CONFIG_REL_PATH}/${INTERNAL_REST_PROTOCOL}-internal-rest-server.cloudify" "/etc/nginx/conf.d/${INTERNAL_REST_PROTOCOL}-internal-rest-server.cloudify"
deploy_blueprint_resource "${CONFIG_REL_PATH}/nginx.conf" "/etc/nginx/nginx.conf"
deploy_blueprint_resource "${CONFIG_REL_PATH}/default.conf" "/etc/nginx/conf.d/default.conf"
deploy_blueprint_resource "${CONFIG_REL_PATH}/rest-location.cloudify" "/etc/nginx/conf.d/rest-location.cloudify"
deploy_blueprint_resource "${CONFIG_REL_PATH}/fileserver-location.cloudify" "/etc/nginx/conf.d/fileserver-location.cloudify"
deploy_blueprint_resource "${CONFIG_REL_PATH}/ui-locations.cloudify" "/etc/nginx/conf.d/ui-locations.cloudify"
deploy_blueprint_resource "${CONFIG_REL_PATH}/logs-conf.cloudify" "/etc/nginx/conf.d/logs-conf.cloudify"

sudo systemctl enable nginx.service &>/dev/null
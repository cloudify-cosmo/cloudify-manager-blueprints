#!/bin/bash -e

. $(ctx download-resource "components/utils")
. $(ctx download-resource "components/elasticsearch/scripts/configure_es")


CONFIG_REL_PATH="components/elasticsearch/config"

export ES_JAVA_OPTS=$(ctx node properties es_java_opts)
export ES_HEAP_SIZE=$(ctx node properties es_heap_size)
export ES_HEAP_SIZE=${ES_HEAP_SIZE:-1g}
export ES_ENDPOINT_IP=$(ctx node properties es_endpoint_ip)
export ES_ENDPOINT_PORT=$(ctx node properties es_endpoint_port)

export ES_SOURCE_URL=$(ctx node properties es_rpm_source_url)
export ES_CURATOR_RPM_SOURCE_URL=$(ctx node properties es_curator_rpm_source_url)

# this will be used only if elasticsearch-curator is not installed via an rpm
export ES_CURATOR_VERSION="3.2.3"

export ES_HOME="/opt/elasticsearch"
export ES_LOGS_PATH="/var/log/cloudify/elasticsearch"
export ES_CONF_PATH="/etc/elasticsearch"
ES_UNIT_OVERRIDE="/etc/systemd/system/elasticsearch.service.d"


function install_elasticsearch() {
    ctx logger info "Installing Elasticsearch..."
    set_selinux_permissive

    copy_notice "elasticsearch"
    create_dir ${ES_HOME}
    create_dir ${ES_LOGS_PATH}

    yum_install ${ES_SOURCE_URL}

    ctx logger info "Chowning ${ES_LOGS_PATH} by elasticsearch user..."
    sudo chown -R elasticsearch:elasticsearch ${ES_LOGS_PATH}

    ctx logger info "Creating systemd unit override..."
    create_dir ${ES_UNIT_OVERRIDE}
    deploy_blueprint_resource "${CONFIG_REL_PATH}/restart.conf" "${ES_UNIT_OVERRIDE}/restart.conf"

    ctx logger info "Deploying Elasticsearch Configuration..."
    deploy_blueprint_resource "${CONFIG_REL_PATH}/elasticsearch.yml" "${ES_CONF_PATH}/elasticsearch.yml"
    sudo chown elasticsearch:elasticsearch "${ES_CONF_PATH}/elasticsearch.yml"

    ctx logger info "Deploying Elasticsearch Logging Configuration file..."
    deploy_blueprint_resource "${CONFIG_REL_PATH}/logging.yml" "${ES_CONF_PATH}/logging.yml"
    sudo chown elasticsearch:elasticsearch "${ES_CONF_PATH}/logging.yml"

    # we should treat these as templates.
    ctx logger info "Setting Elasticsearch Heap size..."
    replace "#ES_HEAP_SIZE=2g" "ES_HEAP_SIZE=${ES_HEAP_SIZE}" "/etc/sysconfig/elasticsearch"

    if [ ! -z "${ES_JAVA_OPTS}" ]; then
        ctx logger info "Setting additional Java OPTS..."
        replace "#ES_JAVA_OPTS=" "ES_JAVA_OPTS=${ES_JAVA_OPTS}" "/etc/sysconfig/elasticsearch"
    fi

    ctx logger info "Setting Elasticsearch logs path..."
    replace "#LOG_DIR=/var/log/elasticsearch" "LOG_DIR=${ES_LOGS_PATH}" "/etc/sysconfig/elasticsearch"
    replace "#ES_GC_LOG_FILE=/var/log/elasticsearch/gc.log" "ES_GC_LOG_FILE=${ES_LOGS_PATH}/gc.log" "/etc/sysconfig/elasticsearch"

    deploy_logrotate_config "elasticsearch"

    ctx logger info "Installing Elasticsearch Curator..."
    if [ -z ${ES_CURATOR_RPM_SOURCE_URL} ]; then
        install_module "elasticsearch-curator==${ES_CURATOR_VERSION}"
    else
        yum_install ${ES_CURATOR_RPM_SOURCE_URL}
    fi

    rotator_script=$(ctx download-resource-and-render components/elasticsearch/scripts/rotate_es_indices)

    ctx logger info "Configuring Elasticsearch Index Rotation cronjob for logstash-YYYY.mm.dd index patterns..."
    # testable manually by running: sudo run-parts /etc/cron.daily
    sudo mv ${rotator_script} /etc/cron.daily/rotate_es_indices
    sudo chown -R root:root /etc/cron.daily/rotate_es_indices
    sudo chmod +x /etc/cron.daily/rotate_es_indices

    ctx logger info "Enabling Elasticsearch Service..."
    sudo systemctl enable elasticsearch.service &>/dev/null
}

if [ -z "${ES_ENDPOINT_IP}" ]; then
    ES_ENDPOINT_IP=$(ctx instance host_ip)
    install_elasticsearch

    ctx logger info "Starting Elasticsearch Service..."
    sudo systemctl start elasticsearch.service

    wait_for_port "${ES_ENDPOINT_PORT}" "${ES_ENDPOINT_IP}"
    # per a function in configure_es
    configure_elasticsearch "${ES_ENDPOINT_IP}" "${ES_ENDPOINT_PORT}"

    ctx logger info "Stopping Elasticsearch Service..."
    sudo systemctl stop elasticsearch.service
    clean_var_log_dir elasticsearch
else
    ctx logger info "External Elasticsearch Endpoint provided: ${ES_ENDPOINT_IP}:${ES_ENDPOINT_PORT}..."
    sleep 5
    wait_for_port "${ES_ENDPOINT_PORT}" "${ES_ENDPOINT_IP}"
    ctx logger info "Checking if 'cloudify_storage' index already exists..."
    if curl --fail --silent -XHEAD -i "http://${ES_ENDPOINT_IP}:${ES_ENDPOINT_PORT}/cloudify_storage" >/dev/null; then
        sys_error "'cloudify_storage' index already exists on ${ES_ENDPOINT_IP}, terminating bootstrap..."
    fi
    # per a function in configure_es
    configure_elasticsearch "${ES_ENDPOINT_IP}" "${ES_ENDPOINT_PORT}"
fi

ctx instance runtime_properties es_endpoint_ip ${ES_ENDPOINT_IP}

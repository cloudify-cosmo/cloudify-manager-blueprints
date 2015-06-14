#!/bin/bash -e

export LOGSTASH_VERSION="1.4.2"
export LOGSTASH_HOME="/opt/logstash"
export LOGSTASH_LOG_PATH="/var/log/cloudify/logstash"
# export LOGSTASH_SOURCE_URL=$(ctx node properties logstash_tar_source_url)
export LOGSTASH_SOURCE_URL="https://download.elasticsearch.org/logstash/logstash/logstash-${LOGSTASH_VERSION}.tar.gz"


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
    ctx logger info "Installing Logstash..."

    copy_notice "logstash" && \
    create_dir ${LOGSTASH_HOME} && \
    create_dir ${LOGSTASH_LOG_PATH} && \

    download_file ${LOGSTASH_SOURCE_URL} "/tmp/logstash.tar.gz" && \
    ctx logger info "Extracting Logstash..."
    sudo tar -C ${LOGSTASH_HOME} -xzvf "/tmp/logstash.tar.gz" --strip-components=1 && \
    clean_tmp

    # ctx download-resource "components/logstash/config/logstash.conf" '@{"target_path": "/tmp/logstash.conf"}'
    sudo cp "components/logstash/config/logstash.conf" "/tmp/logstash.conf" && \
    sudo mv "/tmp/logstash.conf" "${LOGSTASH_HOME}/logstash.conf"
}

cd /vagrant
import_helpers
main
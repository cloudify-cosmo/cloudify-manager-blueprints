#!/bin/bash -e


export NODEJS_VERSION="0.10.35"
export NODEJS_HOME="/opt/nodejs"
export WEBUI_HOME="/opt/cloudify-ui"
export WEBUI_LOG_PATH="/var/log/cloudify/webui"
export GRAFANA_HOME="${WEBUI_HOME}/grafana"
export NODEJS_SOURCE_URL="http://nodejs.org/dist/v${NODEJS_VERSION}/node-v${NODEJS_VERSION}-linux-x64.tar.gz"
# export NODEJS_SOURCE_URL=$(ctx node properties nodejs_tar_source_url)
export WEBUI_SOURCE_URL="https://dl.dropboxusercontent.com/u/407576/cosmo-ui-3.2.0-m4.tgz"
# export WEBUI_SOURCE_URL=$(ctx node properties webui_source_url)
export GRAFANA_SOURCE_URL="https://dl.dropboxusercontent.com/u/407576/grafana-1.9.0.tgz"
# export GRAFANA_SOURCE_URL=$(ctx node properties grafana_source_url)


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
    ctx logger info "Installing Cloudify's WebUI..."

    copy_notice "webui"
    sudo cp components/webui/LICENSE /opt/LICENSE

    create_dir ${NODEJS_HOME}
    create_dir ${WEBUI_HOME}
    create_dir ${WEBUI_HOME}/backend
    create_dir ${WEBUI_LOG_PATH}
    create_dir ${GRAFANA_HOME}

    ctx logger info "Installing NodeJS..."
    download_file ${NODEJS_SOURCE_URL} "/tmp/nodejs.tar.gz"
    sudo tar -xzvf "/tmp/nodejs.tar.gz" -C ${NODEJS_HOME} --strip-components=1

    ctx logger info "Installing Cloudify's WebUI..."
    download_file ${WEBUI_SOURCE_URL} "/tmp/webui.tgz"
    sudo tar -xzvf "/tmp/webui.tgz" -C ${WEBUI_HOME} --strip-components=1
    ctx logger info "Applying Workaround for missing dependencies..."
    sudo ${NODEJS_HOME}/bin/npm install --prefix ${WEBUI_HOME} request tar
    clean_tmp

    ctx logger info "Installing Grafana..."
    download_file ${GRAFANA_SOURCE_URL} "/tmp/grafana.tgz"
    sudo tar -xzvf "/tmp/grafana.tgz" -C ${GRAFANA_HOME} --strip-components=1

    ctx logger info "Deploying WebUI Configuration..."
    sudo cp "components/webui/config/gsPresets.json" "${WEBUI_HOME}/backend/gsPresets.json"
    ctx logger info "Deploying Grafana Configuration..."
    sudo cp "components/webui/config/config.js" "${GRAFANA_HOME}/"
}

cd /vagrant
import_helpers
main
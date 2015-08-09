#!/bin/bash -e

. $(ctx download-resource "components/utils")


CONFIG_REL_PATH="components/webui/config"

export NODEJS_SOURCE_URL=$(ctx node properties nodejs_tar_source_url)  # (e.g. "http://nodejs.org/dist/v0.10.35/node-v0.10.35-linux-x64.tar.gz")
export WEBUI_SOURCE_URL=$(ctx node properties webui_tar_source_url)  # (e.g. "https://dl.dropboxusercontent.com/u/407576/cosmo-ui-3.2.0-m4.tgz")
export GRAFANA_SOURCE_URL=$(ctx node properties grafana_tar_source_url)  # (e.g. "https://dl.dropboxusercontent.com/u/407576/grafana-1.9.0.tgz")

export NODEJS_HOME="/opt/nodejs"
export WEBUI_HOME="/opt/cloudify-ui"
export WEBUI_LOG_PATH="/var/log/cloudify/webui"
export GRAFANA_HOME="${WEBUI_HOME}/grafana"
export WEBUI_USER="webui"
export WEBUI_GROUP="webui"

ctx logger info "Installing Cloudify's WebUI..."

copy_notice "webui"
webui_notice=$(ctx download-resource "components/webui/LICENSE")
sudo mv ${webui_notice} "/opt/LICENSE"

create_dir ${NODEJS_HOME}
create_dir ${WEBUI_HOME}
create_dir ${WEBUI_HOME}/backend
create_dir ${WEBUI_LOG_PATH}
create_dir ${GRAFANA_HOME}

ctx logger info "Creating user..."
sudo useradd --shell /sbin/nologin --home-dir "${WEBUI_HOME}" --no-create-home --system "${WEBUI_USER}"

ctx logger info "Installing NodeJS..."
nodejs=$(download_file ${NODEJS_SOURCE_URL})
sudo tar -xzvf ${nodejs} -C ${NODEJS_HOME} --strip-components=1 >/dev/null

ctx logger info "Installing Cloudify's WebUI..."
webui=$(download_file ${WEBUI_SOURCE_URL})
sudo tar -xzvf ${webui} -C ${WEBUI_HOME} --strip-components=1 >/dev/null
# ctx logger info "Applying Workaround for missing dependencies..."
# sudo ${NODEJS_HOME}/bin/npm install --prefix ${WEBUI_HOME} request tar >/dev/null

ctx logger info "Installing Grafana..."
grafana=$(download_file ${GRAFANA_SOURCE_URL})
sudo tar -xzvf ${grafana} -C ${GRAFANA_HOME} --strip-components=1 >/dev/null

ctx logger info "Deploying WebUI Configuration..."
deploy_file "${CONFIG_REL_PATH}/gsPresets.json" "${WEBUI_HOME}/backend/gsPresets.json"
ctx logger info "Deploying Grafana Configuration..."
deploy_file "${CONFIG_REL_PATH}/grafana_config.js" "${GRAFANA_HOME}/config.js"

ctx logger info "Configuring logrotate..."
lconf="/etc/logrotate.d/cloudify-webui"

ctx logger info "Fixing permissions..."
sudo chown -R "${WEBUI_USER}:${WEBUI_GROUP}" "${WEBUI_HOME}"
sudo chown -R "${WEBUI_USER}:${WEBUI_GROUP}" "${NODEJS_HOME}"
sudo chown -R "${WEBUI_USER}:${WEBUI_GROUP}" "${WEBUI_LOG_PATH}"

cat << EOF | sudo tee $lconf >/dev/null
$WEBUI_LOG_PATH/*.log {
        daily
        rotate 7
        copytruncate
        compress
        delaycompress
        missingok
        notifempty
}
EOF

sudo chmod 644 $lconf


configure_systemd_service "webui"
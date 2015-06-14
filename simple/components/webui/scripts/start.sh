#!/bin/bash -e

export NODEJS_HOME=/opt/nodejs
export WEBUI_HOME=/opt/cloudify-ui

ctx logger info "Starting WebUI Backend..."
sudo ${NODEJS_HOME}/bin/node ${WEBUI_HOME}/cosmoui.js localhost > /dev/null 2>&1 &
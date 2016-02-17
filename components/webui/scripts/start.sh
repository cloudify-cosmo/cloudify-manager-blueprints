#!/bin/bash -e

ctx logger info "Starting WebUI Backend..."
sudo systemctl start cloudify-webui.service

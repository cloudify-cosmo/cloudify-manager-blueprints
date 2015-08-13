#!/bin/bash -e

ctx logger info "Starting WebUI Backend..."
sudo systemctl start cloudify-webui.service

ctx logger info "Starting Kibana..."
sudo bash /opt/cloudify-ui/kibana/run.sh

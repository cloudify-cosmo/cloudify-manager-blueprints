#!/bin/bash -e

. $(ctx download-resource "components/utils")

ctx logger info "Creating Management Worker Service..."
configure_systemd_service "mgmtworker"
ctx logger info "Starting Management Worker..."
sudo systemctl start cloudify-mgmtworker.service
# sudo ${MGMTWORKER_HOME}/startup.sh
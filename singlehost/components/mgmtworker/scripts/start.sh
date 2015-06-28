#!/bin/bash -e

ctx logger info "Starting Management Worker..."
sudo systemctl start cloudify-mgmtworker.service
# sudo ${MGMTWORKER_HOME}/startup.sh
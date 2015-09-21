#!/bin/bash -e

ctx logger info "Starting Management Worker Service..."
sudo systemctl start cloudify-mgmtworker.service

#!/bin/bash -e

ctx logger info "Stopping Management Worker Service..."
sudo systemctl stop cloudify-mgmtworker.service

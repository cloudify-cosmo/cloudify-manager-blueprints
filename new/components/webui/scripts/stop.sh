#!/bin/bash -e

ctx logger info "Stopping WebUI Backend..."
sudo systemctl stop cloudify-webui.service

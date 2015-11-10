#!/bin/bash -e

ctx logger info "Stopping Riemann..."
sudo systemctl stop cloudify-riemann.service
#!/bin/bash -e

ctx logger info "Starting Rest Service via Gunicorn..."
sudo systemctl start cloudify-restservice.service

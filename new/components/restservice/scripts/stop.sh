#!/bin/bash -e

ctx logger info "Stopping Rest Service via Gunicorn..."
sudo systemctl stop cloudify-restservice.service
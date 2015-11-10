#!/bin/bash -e

ctx logger info "Stopping Nginx Service..."
sudo systemctl stop nginx.service

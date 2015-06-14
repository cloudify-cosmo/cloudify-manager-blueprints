#!/bin/bash -e

ctx logger info "Starting Nginx..."
sudo nginx -c /etc/nginx/nginx.conf & # -g "daemon off;"
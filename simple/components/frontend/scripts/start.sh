#!/bin/bash -e

ctx logger info "Starting Nginx..."
# nohup sudo nginx -c /etc/nginx/nginx.conf >& /dev/null < /dev/null & # -g "daemon off;"
sudo systemctl start nginx
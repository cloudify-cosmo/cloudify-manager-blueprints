#!/bin/bash -e

ctx logger info "Stopping Elasticsearch Service..."
sudo systemctl stop elasticsearch.service
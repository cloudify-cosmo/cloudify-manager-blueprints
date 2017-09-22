#!/bin/bash -e

export CLI_SOURCE_URL=$(ctx node properties cli_source_url)

ctx logger info "Installing CLI RPM from ${CLI_SOURCE_URL}..."
sudo yum -y install ${CLI_SOURCE_URL}

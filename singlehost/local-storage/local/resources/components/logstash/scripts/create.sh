#!/bin/bash -e

. $(ctx download-resource "components/utils")


export LOGSTASH_SOURCE_URL=$(ctx node properties logstash_tar_source_url)  # (e.g. "https://download.elasticsearch.org/logstash/logstash/logstash-1.4.2.tar.gz")

# export LOGSTASH_HOME="/opt/logstash"
export LOGSTASH_LOG_PATH="/var/log/cloudify/logstash"
export LOGSTASH_CONF_PATH="/etc/logstash/conf.d"


ctx logger info "Installing Logstash..."

copy_notice "logstash"
create_dir ${LOGSTASH_LOG_PATH}

yum_install ${LOGSTASH_SOURCE_URL}

logstash_conf=$(ctx download-resource "components/logstash/config/logstash.conf")
sudo mv ${logstash_conf} "${LOGSTASH_CONF_PATH}/logstash.conf"

lconf="/etc/logrotate.d/logstash"
config="$LOGSTASH_LOG_PATH/*.log {
        daily
        rotate 7
        copytruncate
        compress
        delaycompress
        missingok
        notifempty
}"

ctx logger info "Configuring logrotate..."
echo "$config" | sudo tee $lconf
sudo chmod 644 $lconf

# sudo systemctl enable logstash.service
sudo /sbin/chkconfig logstash on
#!/bin/bash

# export LOGSTASH_HOME="/opt/logstash"
# export LOGSTASH_LOG_PATH="/var/log/cloudify/logstash"

ctx logger info "Starting Logstash..."
# nohup sudo ${LOGSTASH_HOME}/bin/logstash -f ${LOGSTASH_HOME}/logstash.conf -l ${LOGSTASH_LOG}/logstash.log --verbose >& /dev/null < /dev/null &
# sudo systemctl start logstash.service
sudo /etc/init.d/logstash start
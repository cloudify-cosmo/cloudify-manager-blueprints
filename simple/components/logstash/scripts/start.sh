#!/bin/bash

export LOGSTASH_HOME="/opt/logstash"
export LOGSTASH_LOG_PATH="/var/log/cloudify/logstash"

ctx logger info "Starting Logstash..."
sudo ${LOGSTASH_HOME}/bin/logstash -f ${LOGSTASH_HOME}/logstash.conf -l ${LOGSTASH_LOG}/logstash.log --verbose > /dev/null 2>&1 &
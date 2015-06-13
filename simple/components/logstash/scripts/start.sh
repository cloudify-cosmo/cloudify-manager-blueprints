#!/bin/bash

LOGSTASH_HOME="/opt/logstash"
LOGSTASH_LOG_PATH="/var/log/cloudify/logstash"

sudo ${LOGSTASH_HOME}/bin/logstash -f ${LOGSTASH_HOME}/logstash.conf -l ${LOGSTASH_LOG}/logstash.log --verbose &
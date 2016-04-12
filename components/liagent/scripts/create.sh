#!/bin/bash -e

. $(ctx download-resource "components/utils")

CONFIG_REL_PATH="components/liagent/config"
export LIAGENT_CONF_PATH="/var/lib/loginsight-agent"

export LIAGENT_SOURCE_URL=$(ctx node properties liagent_rpm_source_url)

ctx logger info "Installing Log Insight agent..."

set_selinux_permissive

#copy_notice "logstash"

yum_install ${LIAGENT_SOURCE_URL}
sudo systemctl stop liagentd
ctx logger info "Deploying Log Insight agent conf..."
deploy_blueprint_resource "${CONFIG_REL_PATH}/liagent.ini" "${LIAGENT_CONF_PATH}/liagent.ini"

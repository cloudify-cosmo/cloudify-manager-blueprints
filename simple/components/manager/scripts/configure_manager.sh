#!/bin/bash -e

. $(ctx download-resource "components/utils")


export PROVIDER_CONTEXT_FILE=$(ctx download-resource "components/manager/config/provider_context")
export PROVIDER_CONTEXT_DATA=$(cat $PROVIDER_CONTEXT_FILE)

ctx instance runtime_properties manager_provider_context "$PROVIDER_CONTEXT_DATA"

ctx logger info "Posting Provider Context..."
# should probably use $(ctx instance runtime_properties host_ip) instread of localhost(?)
curl --fail --silent --request POST --data @${PROVIDER_CONTEXT_FILE} http://localhost/provider/context --header "Content-Type:application/json" >/dev/null




# REMOVE, TEST ONLY!
# test for when requiretty is enabled and the disable-requiretty script should disable it.
# replace "#Defaults requiretty" "Defaults requiretty" "/etc/sudoers"
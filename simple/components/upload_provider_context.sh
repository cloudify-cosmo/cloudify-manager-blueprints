#!/bin/bash -e

export PROVIDER_CONTEXT_FILE=$(ctx download-resource "components/provider_context")
export PROVIDER_CONTEXT_DATA=$(cat $PROVIDER_CONTEXT_FILE)

ctx instance runtime_properties provider_context "$PROVIDER_CONTEXT_DATA"

ctx logger info "Posting Provider Context..."
# should probably use $(ctx instance runtime-properties host_ip) instread of localhost(?)
curl --fail --request POST --data @${PROVIDER_CONTEXT_FILE} http://localhost/provider/context --header "Content-Type:application/json"

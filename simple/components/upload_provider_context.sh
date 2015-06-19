#!/bin/bash -e

export PROVIDER_CONTEXT_FILE=$(ctx download-resource "components/provider_context")

ctx logger info "Posting Provider Context..."
# should probably use $(ctx instance runtime-properties host_ip) instread of localhost(?)
curl --fail --request POST --data @${PROVIDER_CONTEXT_FILE} http://localhost/provider/context --header "Content-Type:application/json"
#!/bin/bash -e

export CONTEXT_FILE_PATH="components/provider_context"

ctx logger info "Posting Provider Context..."
curl --fail --request POST --data @${CONTEXT_FILE_PATH} http://localhost/provider/context --header "Content-Type:application/json"
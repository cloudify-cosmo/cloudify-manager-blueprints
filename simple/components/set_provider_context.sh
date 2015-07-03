#!/bin/bash -e

ctx logger info "Setting Provider Context Runtime Property."
PROVIDER_CONTEXT=$(ctx target instance runtime_properties provider_context)
ctx source instance runtime_properties manager_provider_context "${PROVIDER_CONTEXT}"
#!/bin/bash -e
. $(ctx download-resource "components/utils")

ctx logger info "Starting mgmt-worker preconfigure.sh..."
rest_port=$(ctx target instance runtime-properties rest_port)
ctx source instance runtime_properties rest_port ${rest_port}
verify_certificate=$(ctx target instance runtime-properties verify_certificate)
ctx source instance runtime_properties rest_port ${verify_certificate}

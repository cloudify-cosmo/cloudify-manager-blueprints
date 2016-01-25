#!/bin/bash -e
. $(ctx download-resource "components/utils")

internal_protocol=$(ctx target instance runtime-properties internal_rest_protocol)
ctx logger info "Riemann uses REST protocol: ${internal_protocol}"
ctx source instance runtime-properties internal_rest_protocol ${internal_protocol}
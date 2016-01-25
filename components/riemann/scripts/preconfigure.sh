#!/bin/bash -e
. $(ctx download-resource "components/utils")

ctx source instance runtime-properties internal_rest_protocol $(ctx target instance runtime-properties internal_rest_protocol)
#!/bin/bash -e

. $(ctx download-resource "components/utils")
configure_systemd_service "mgmtworker"
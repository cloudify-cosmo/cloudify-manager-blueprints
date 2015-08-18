#!/bin/bash -e

ctx logger info "Setting Manager IP Runtime Property."
MANAGER_IP=$(ctx target instance host_ip)
ctx logger info "Manager IP is: ${MANAGER_IP}"
ctx source instance runtime_properties manager_host_ip ${MANAGER_IP}
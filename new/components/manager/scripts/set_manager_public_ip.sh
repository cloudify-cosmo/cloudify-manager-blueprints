#!/bin/bash -e

ctx logger info "Setting Public Manager IP Runtime Property."
MANAGER_IP=${public_ip}
ctx logger info "Manager Public IP is: ${MANAGER_IP}"
ctx source instance runtime_properties public_ip ${MANAGER_IP}
#!/bin/bash -e

ctx logger info "Using localhost as Manager..."

#mongo_ip_address=$(ctx target instance host_ip)
username=$(ctx instance runtime_properties admin_username)
password=$(ctx instance runtime_properties admin_password)
cfy profiles use localhost -u $username -p $password -t default_tenant

# sudo -u root cfy profiles use localhost -u $username -p $password -t default_tenant

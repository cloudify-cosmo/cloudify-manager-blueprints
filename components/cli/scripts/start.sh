#!/bin/bash -e

manager_username="$1"
manager_password="$2"

echo "Using localhost as Manager..."

cfy profiles use localhost -u $manager_username -p $manager_password -t default_tenant

sudo -u root cfy profiles use localhost -u $manager_username -p $manager_password -t default_tenant

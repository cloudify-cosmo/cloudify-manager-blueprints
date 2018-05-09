#!/bin/bash -e

manager_username="{{ username }}"
manager_password="{{ password }}"

echo "Using localhost as Manager..."
cfy profiles use localhost -u $manager_username -p $manager_password -t default_tenant

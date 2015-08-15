#!/bin/bash

cfy blueprints upload -b Manager -p simple-manager-blueprint.yaml -v
cfy deployments create -b Manager -d Manager --inputs inputs.yaml -v

cd /tmp
wget https://github.com/cloudify-cosmo/cloudify-nodecellar-example/archive/3.3m3.tar.gz -O /tmp/nc.tar.gz
tar -xzvf /tmp/nc.tar.gz
cd cloudify-nodecellar-example-3.3m3/

# local - if you want to deploy on the same machine your manager is on
# echo '
# host_ip: 10.10.1.10
# agent_user: vagrant
# agent_private_key_path: ~/.ssh/test_private_key
# ' >> inputs/nodecellar-singlehost.yaml

#remote - deploying on an externally provisioned machine
echo 'host_ip: "10.10.1.11"
agent_user: "vagrant"
agent_private_key_path: "/home/vagrant/.ssh/test_private_key"' >> inputs/nodecellar-singlehost.yaml

cfy init
cfy use -t 10.10.1.10
cfy blueprints upload -b $1 -p singlehost-blueprint.yaml
cfy deployments create -b $1 -d $1 --inputs inputs/nodecellar-singlehost.yaml
cfy executions start -w install -d $1


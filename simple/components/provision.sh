#!/bin/bash

function update_local_cache
{
    sudo yum -y update
}


update_local_cache
sudo yum install python-devel g++ gcc -y

curl --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo python
sudo pip install virtualenv
virtualenv cfy
source cfy/bin/activate
pip install cloudify==3.2
wget https://github.com/cloudify-cosmo/cloudify-manager-blueprints/archive/componentized-simple-manager-blueprint.tar.gz
tar -xzvf componentized-simple-manager-blueprint.tar.gz
cd cloudify-manager-blueprints-componentized-simple-manager-blueprint/
cd simple/
# cfy local init --blueprint-path simple-manager-blueprint.yaml --inputs inputs.yaml.template
# cfy local execute -w install



cd /vagrant






# components/install_manager_components.sh
# components/start_manager_components.sh

# sudo yum install python-devel gcc g++ -y
# cd ~
# virtualenv cfy
# source cfy/bin/activate
# pip install cloudify==3.2

# sudo mkdir /root/.ssh
# ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N ''
# cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
# sudo cp ~/.ssh/id_rsa /root/.ssh

# mkdir -p ~/cloudify/blueprints/inputs/

# cd /vagrant/components
# echo '
# host_ip: 10.10.1.10
# agent_user: vagrant
# agent_private_key_path: /root/.ssh/id_rsa
# ' >> ~/cloudify/blueprints/inputs/nodecellar-singlehost.yaml

# cfy blueprints upload -b nodecellar -p singlehost-blueprint.yaml
# cfy deployments create -b nodecellar -d nodecellar --inputs ~/cloudify/blueprints/inputs/nodecellar-singlehost.yaml
# cfy executions start -w install -d nodecellar
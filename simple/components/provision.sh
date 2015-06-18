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

wget http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/get-cloudify.py
python get-cloudify.py -v -f

cd /vagrant
source ~/cfy/bin/activate
cfy local init --blueprint-path simple-manager-blueprint.yaml --inputs inputs.yaml.template
cfy local execute -w install -v






# cd /vagrant
# components/install_manager_components.sh
# components/start_manager_components.sh

# sudo yum install python-devel gcc g++ -y

# sudo mkdir /root/.ssh
# ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N ''
# cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
# sudo cp ~/.ssh/id_rsa /root/.ssh/id_rsa

# wget https://github.com/cloudify-cosmo/cloudify-nodecellar-example/archive/3.2.tar.gz
# tar -xzvf 3.2.tar.gz
# cd cloudify-nodecellar-example-3.2/

# echo '
# host_ip: 10.10.1.10
# agent_user: vagrant
# agent_private_key_path: /root/.ssh/id_rsa
# ' >> inputs/nodecellar-singlehost.yaml

# cfy init
# cfy use -t localhost
# cfy blueprints upload -b nodecellar -p singlehost-blueprint.yaml
# cfy deployments create -b nodecellar -d nodecellar --inputs inputs/nodecellar-singlehost.yaml
# cfy executions start -w install -d nodecellar
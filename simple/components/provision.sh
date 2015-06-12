#!/bin/bash

function update_local_cache
{
    sudo yum -y update
}

function cleanup
{
    sudo yum clean all
    sudo yum remove curl -y
    sudo yum autoremove -y
}


function upload_provider_context
{
    curl --fail --request POST --data @components/provider_context http://localhost/provider/context --header "Content-Type:application/json"
}

update_local_cache

cd /vagrant
# . components/env_vars
# . components/utils

# components/java/scripts/create.sh
# components/python/scripts/create.sh
# components/rabbitmq/scripts/create.sh
# components/elasticsearch/scripts/create.sh
# components/logstash/scripts/create.sh
# components/influxdb/scripts/create.sh
# components/frontend/scripts/create.sh
# components/riemann/scripts/create.sh
# components/restservice/scripts/create.sh
# components/mgmtworker/scripts/create.sh
# components/amqpinflux/scripts/create.sh
# components/webui/scripts/create.sh

start_rabbitmq
start_elasticsearch
start_logstash
start_influxdb
start_nginx
start_riemann
start_restservice
start_mgmtworker
start_amqpinflux
start_webui
upload_provider_context

sudo yum install python-devel gcc g++ -y
cd ~
virtualenv cfy
source cfy/bin/activate
pip install cloudify==3.2

sudo mkdir /root/.ssh
ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N ''
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
sudo cp ~/.ssh/id_rsa /root/.ssh

mkdir -p ~/cloudify/blueprints/inputs/

cd /vagrant/components
echo '
host_ip: 10.10.1.10
agent_user: vagrant
agent_private_key_path: /root/.ssh/id_rsa
' >> ~/cloudify/blueprints/inputs/nodecellar-singlehost.yaml

cfy blueprints upload -b nodecellar -p singlehost-blueprint.yaml
cfy deployments create -b nodecellar -d nodecellar --inputs ~/cloudify/blueprints/inputs/nodecellar-singlehost.yaml
cfy executions start -w install -d nodecellar
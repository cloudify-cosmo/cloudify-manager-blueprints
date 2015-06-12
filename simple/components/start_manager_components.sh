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

cd /vagrant

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

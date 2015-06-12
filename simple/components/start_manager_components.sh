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

components/rabbitmq/scripts/start.sh
components/elasticsearch/scripts/start.sh
components/logstash/scripts/start.sh
components/influxdb/scripts/start.sh
components/frontend/scripts/start.sh
components/riemann/scripts/start.sh
components/restservice/scripts/start.sh
components/mgmtworker/scripts/start.sh
components/amqpinflux/scripts/start.sh
sleep 5
components/webui/scripts/start.sh
upload_provider_context

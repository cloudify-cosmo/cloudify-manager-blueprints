#!/bin/bash

function update_local_cache
{
    sudo yum -y update
}

update_local_cache

cd /vagrant

components/java/scripts/create.sh
components/python/scripts/create.sh
components/rabbitmq/scripts/create.sh
components/elasticsearch/scripts/create.sh
components/logstash/scripts/create.sh
components/influxdb/scripts/create.sh
components/frontend/scripts/create.sh
components/riemann/scripts/create.sh
components/restservice/scripts/create.sh
components/mgmtworker/scripts/create.sh
components/amqpinflux/scripts/create.sh
components/webui/scripts/create.sh

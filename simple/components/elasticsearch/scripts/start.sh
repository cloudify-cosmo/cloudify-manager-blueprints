#!/bin/bash

ELASTICSEARCH_HOME="/opt/elasticsearch"

function main
{
    sudo ${ELASTICSEARCH_HOME}/bin/elasticsearch -d
}

main

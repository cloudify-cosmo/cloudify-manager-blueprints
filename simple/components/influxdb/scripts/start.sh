#!/bin/bash

INFLUXDB_HOME="/opt/influxdb"

function main
{
    sudo /usr/bin/influxdb-daemon -config=${INFLUXDB_HOME}/shared/config.toml
}

main

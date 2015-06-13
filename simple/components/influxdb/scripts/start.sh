#!/bin/bash

INFLUXDB_HOME="/opt/influxdb"

sudo /usr/bin/influxdb -config=${INFLUXDB_HOME}/shared/config.toml &

#!/bin/bash -e

uname -a

# add http(s) rules
firewall-cmd --zone=public --add-port=80/tcp --permanent
firewall-cmd --zone=public --add-port=443/tcp --permanent
# add influxdb connection
firewall-cmd --zone=public --add-port=8086/tcp --permanent
# port for agent download
firewall-cmd --zone=public --add-port=53229/tcp --permanent
# port for AQMP
firewall-cmd --zone=public --add-port=5672/tcp --permanent
# port for diamond
firewall-cmd --zone=public --add-port=8101/tcp --permanent
firewall-cmd --zone=public --add-port=8100/tcp --permanent

firewall-cmd --reload

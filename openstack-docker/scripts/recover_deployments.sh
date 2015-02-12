#!/bin/bash

ls /etc/init.d | grep celeryd- | while read line ;
do
    sudo service "$line" start ;
done

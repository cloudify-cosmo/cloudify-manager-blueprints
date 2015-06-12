#!/bin/bash

function main
{
    sudo nginx -c /etc/nginx/nginx.conf & # -g "daemon off;"
}

main
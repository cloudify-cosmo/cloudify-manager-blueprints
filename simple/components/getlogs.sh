#!/bin/bash
LOGS_DEST="./logs"
LOGS_PATH="/var/log/cloudify"

for cid in $(docker ps --filter status=running --quiet)
do
    cname=$(docker inspect --format='{{.Name}}' $cid)
    cname=${cname:1}
    docker cp $cid:$LOGS_PATH $LOGS_DEST 2>/dev/null
    if [ $? -eq 0 ]; then
        mv $LOGS_DEST/cloudify $LOGS_DEST/$cname
    fi
done

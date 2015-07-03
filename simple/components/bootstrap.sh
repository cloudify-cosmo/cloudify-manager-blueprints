#!/bin/bash

# source ~/cfy/bin/activate
# cfy local init --blueprint-path simple-manager-blueprint.yaml --inputs inputs.yaml --install-plugins
# cfy local execute -w install -v

cfy init -r
cfy bootstrap --install-plugins -p simple-manager-blueprint.yaml -i inputs.yaml --keep-up-on-failure

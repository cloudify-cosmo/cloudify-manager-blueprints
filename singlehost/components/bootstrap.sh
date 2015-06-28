#!/bin/bash

# source ~/cfy/bin/activate
cfy local init --blueprint-path simple-manager-blueprint.yaml --inputs inputs.yaml.template --install-plugins
cfy local execute -w install -v

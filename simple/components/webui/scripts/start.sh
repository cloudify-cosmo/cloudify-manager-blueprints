#!/bin/bash

NODEJS_HOME=/opt/nodejs
WEBUI_HOME=/opt/cloudify-ui

sudo ${NODEJS_HOME}/bin/node ${WEBUI_HOME}/cosmoui.js localhost &
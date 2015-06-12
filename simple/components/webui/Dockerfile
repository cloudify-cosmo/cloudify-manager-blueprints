FROM debian:jessie
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

ENV DOCKER_ENV=True \
    NODEJS_VERSION=0.10.35 \
    NODEJS_HOME=/opt/nodejs \
    WEBUI_HOME=/opt/cloudify-ui

RUN apt-get update && \
    apt-get install curl -y --no-install-recommends && \
    mkdir -p ${NODEJS_HOME} && \
    mkdir -p /var/log/cloudify/uibackend && \
    mkdir -p ${WEBUI_HOME}/grafana && \
    curl --fail --silent http://nodejs.org/dist/v${NODEJS_VERSION}/node-v${NODEJS_VERSION}-linux-x64.tar.gz -o /tmp/nodejs.tar.gz && \
    tar -xzvf /tmp/nodejs.tar.gz -C ${NODEJS_HOME} --strip-components=1 && \
    curl --fail --silent http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/3.2.0/m4-RELEASE/cloudify-ui_3.2.0-m4-b173_amd64.deb -o /tmp/cloudify-webui.deb && \
    dpkg-deb -x /tmp/cloudify-webui.deb /tmp/cloudify-webui/ && \
    tar -xzvf /tmp/cloudify-webui/packages/cloudify-ui/cosmo-ui* -C ${WEBUI_HOME} --strip-components=1 && \
    tar -xzvf /tmp/cloudify-webui/packages/cloudify-ui/grafana* -C ${WEBUI_HOME}/grafana --strip-components=1 && \
    cp /tmp/cloudify-webui/packages/cloudify-ui/config/grafana/config.js ${WEBUI_HOME}/grafana/ && \
    # current workaround for missing dependency
    ${NODEJS_HOME}/bin/npm install --prefix ${WEBUI_HOME} request tar && \
    rm -rf /var/lib/apt/lists && \
    rm -rf /tmp/* && \
    apt-get purge -y curl && \
    apt-get autoremove -y

COPY LICENSE /opt/cloudify-ui/LICENSE
COPY config/gsPresets.json /opt/cloudify-ui/backend/gsPresets.json

EXPOSE 9001
VOLUME ${WEBUI_HOME}

CMD ${NODEJS_HOME}/bin/node ${WEBUI_HOME}/cosmoui.js localhost
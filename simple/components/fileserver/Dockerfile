FROM debian:jessie
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

ENV DOCKER_ENV=True \
    MANAGER_VERSION=master \
    RESOURCES_HOME=/opt/manager/resources

RUN apt-get update && \
    apt-get install -y curl sudo && \
    mkdir -p ${RESOURCES_HOME} && \
    curl --fail -L --create-dirs -o /tmp/cloudify-manager/manager.tar.gz https://github.com/cloudify-cosmo/cloudify-manager/archive/${MANAGER_VERSION}.tar.gz && \
    tar -xzf /tmp/cloudify-manager/manager.tar.gz --strip-components=1 -C /tmp/cloudify-manager/ && \
    cp -r /tmp/cloudify-manager/resources/rest-service/* ${RESOURCES_HOME} && \
    rm -rf /var/lib/apt/lists /tmp/* && \
    apt-get autoremove -y

VOLUME /opt/manager/resources

CMD echo Fileserver
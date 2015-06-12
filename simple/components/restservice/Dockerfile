FROM cloudify_pythonbase
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

ENV DOCKER_ENV=True \
    DSL_VERSION=master \
    REST_CLIENT_VERSION=master \
    COMMON_VERSION=master \
    MANAGER_VERSION=CFY-1838-split-containers \
    SECUREST_VERSION=0.5 \
    MANAGER_HOME=/opt/manager
ENV MANAGER_VIRTUALENV=${MANAGER_HOME}/env \
    MANAGER_REST_CONFIG_PATH=${MANAGER_HOME}/guni.conf

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    mkdir -p ${MANAGER_HOME} && \
    mkdir -p /var/log/cloudify/rest && \
    virtualenv ${MANAGER_VIRTUALENV} && \
    ${MANAGER_VIRTUALENV}/bin/pip install https://github.com/cloudify-cosmo/cloudify-dsl-parser/archive/${DSL_VERSION}.zip && \
    ${MANAGER_VIRTUALENV}/bin/pip install https://github.com/cloudify-cosmo/cloudify-rest-client/archive/${REST_CLIENT_VERSION}.zip && \
    ${MANAGER_VIRTUALENV}/bin/pip install https://github.com/cloudify-cosmo/cloudify-plugins-common/archive/${COMMON_VERSION}.zip && \
    ${MANAGER_VIRTUALENV}/bin/pip install https://github.com/cloudify-cosmo/flask-securest/archive/${SECUREST_VERSION}.zip  && \
    curl --fail --insecure --silent -L -o /tmp/cloudify-manager/manager.tar.gz --create-dirs https://github.com/cloudify-cosmo/cloudify-manager/archive/${MANAGER_VERSION}.tar.gz && \
    tar -xzf /tmp/cloudify-manager/manager.tar.gz --strip-components=1 -C /tmp/cloudify-manager/ && \
    ${MANAGER_VIRTUALENV}/bin/pip install /tmp/cloudify-manager/rest-service && \
    rm -rf /var/lib/apt/lists /tmp/* && \
    apt-get purge -y curl && \
    apt-get autoremove -y

COPY config/guni.conf ${MANAGER_HOME}/guni.conf

EXPOSE 8100

CMD ${MANAGER_VIRTUALENV}/bin/gunicorn  -w $(($(nproc)*2+1)) -b 0.0.0.0:8100 --timeout 300 manager_rest.server:app --log-file /var/log/cloudify/gunicorn.log --access-logfile /var/log/cloudify/gunicorn-access.log
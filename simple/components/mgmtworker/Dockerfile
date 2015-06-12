FROM cloudify_pythonbase
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY MANAGMENT_WORKER_NOTICE.txt /root/MANAGMENT_WORKER_NOTICE.txt

ENV MANAGER_VERSION=master \
    REST_VERSION=master \
    COMMON_VERSION=master \
    SCRIPT_VERSION=master \
    DOCKER_ENV=True \
    MGMTWORKER_HOME=/opt/mgmtworker

ENV MANAGEMENT_IP=frontend \
    VIRTUALENV_DIR=${MGMTWORKER_HOME}/env \
    CELERY_LOG_DIR=/var/log/cloudify/mgmtworker \
    CELERY_WORK_DIR=${MGMTWORKER_HOME}/work \
    RIEMANN_CONFIGS_DIR=/opt/riemann \
    BROKER_URL=amqp://guest:guest@rabbitmq:5672/ \
    MANAGEMENT_USER=root \
    MANAGER_REST_PORT=8100 \
    MANAGER_FILE_SERVER_URL=http://fileserver:53229 \
    MANAGER_FILE_SERVER_BLUEPRINTS_ROOT_URL=http://fileserver:53229/blueprints \
    CELERY_TASK_SERIALIZER=json \
    CELERY_RESULT_SERIALIZER=json \
    CELERY_RESULT_BACKEND=amqp \
    C_FORCE_ROOT=true

COPY /config/startup.sh /root/startup.sh

RUN apt-get update && \
    apt-get install -y python-dev curl g++ sudo wget libxslt-dev libxml2-dev && \
    chmod +x /root/startup.sh && \
    mkdir -p ${CELERY_LOG_DIR} && \
    virtualenv ${VIRTUALENV_DIR} && \
    ${VIRTUALENV_DIR}/bin/pip install celery==3.1.17 && \
    ${VIRTUALENV_DIR}/bin/pip install https://github.com/cloudify-cosmo/cloudify-rest-client/archive/${REST_VERSION}.zip && \
    ${VIRTUALENV_DIR}/bin/pip install https://github.com/cloudify-cosmo/cloudify-plugins-common/archive/${COMMON_VERSION}.zip && \
    ${VIRTUALENV_DIR}/bin/pip install https://github.com/cloudify-cosmo/cloudify-script-plugin/archive/${SCRIPT_VERSION}.zip && \
    curl --silent -L https://github.com/cloudify-cosmo/cloudify-manager/archive/${MANAGER_VERSION}.tar.gz -o /tmp/cloudify-manager.tar.gz && \
    tar -xzf /tmp/cloudify-manager.tar.gz -C /tmp --strip-components=1 && \
    ${VIRTUALENV_DIR}/bin/pip install /tmp/plugins/plugin-installer && \
    ${VIRTUALENV_DIR}/bin/pip install /tmp/plugins/agent-installer && \
    ${VIRTUALENV_DIR}/bin/pip install /tmp/plugins/riemann-controller && \
    ${VIRTUALENV_DIR}/bin/pip install /tmp/workflows && \
    apt-get purge -y python-dev g++ && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /root/.cache /var/lib/apt/lists/* /tmp/* /var/log/apt/*

CMD /root/startup.sh
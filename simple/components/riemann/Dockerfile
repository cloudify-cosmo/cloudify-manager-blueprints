FROM cloudify_javabase:latest
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY RIEMANN_NOTICE.txt /root/RIEMANN_NOTICE.txt

ENV RIEMANN_VERSION=0.2.6 \
    DOCKER_ENV=True \
    PATH=$PATH:/opt/java/bin \
    LANGOHR_HOME=/opt/lib \
    MANAGEMENT_IP='frontend' \
    RABBITMQ_HOST='rabbitmq' \
    RIEMANN_CONFIG_PATH=/etc/riemann
ENV EXTRA_CLASSPATH=${LANGOHR_HOME}/langohr.jar

RUN apt-get update && \
    mkdir -p /var/log/cloudify/riemann && \
    apt-get install -y curl && \
    curl --fail https://s3-eu-west-1.amazonaws.com/gigaspaces-repository-eu/langohr/2.11.0/langohr.jar --create-dirs -o ${EXTRA_CLASSPATH} && \
    chmod 644 ${EXTRA_CLASSPATH} && \
    curl --fail https://aphyr.com/riemann/riemann_${RIEMANN_VERSION}_all.deb -o /tmp/riemann.deb && \
    dpkg -i /tmp/riemann.deb && \
    curl --fail -o ${RIEMANN_CONFIG_PATH}/conf.d/manager.config --create-dirs https://raw.githubusercontent.com/cloudify-cosmo/cloudify-manager/master/plugins/riemann-controller/riemann_controller/resources/manager.config && \
    rm -rf /var/lib/apt/lists && \
    rm /tmp/* && \
    apt-get purge curl -y && \
    apt-get autoremove -y

COPY config/main.clj ${RIEMANN_CONFIG_PATH}/

CMD /usr/bin/riemann -a ${RIEMANN_CONFIG_PATH}/main.clj
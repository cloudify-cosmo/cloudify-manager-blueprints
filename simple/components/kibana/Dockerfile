FROM cloudify_javabase:latest
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY KIBANA_NOTICE.txt /root/KIBANA_NOTICE.txt

ENV KIBANA_VERSION=4.0.0-beta3 \
    DOCKER_ENV=True \
    KIBANA_SERVICE_DIR=/etc/service/kibana

RUN apt-get update && \
    apt-get install -y curl && \
    mkdir -p ${KIBANA_SERVICE_DIR} && \
    curl https://download.elasticsearch.org/kibana/kibana/kibana-${KIBANA_VERSION}.tar.gz --create-dirs -o /opt/tmp/kibana.tar.gz && \
    tar -C ${KIBANA_SERVICE_DIR}/ -xvf /opt/tmp/kibana.tar.gz --strip-components=1 && \
    rm -rf /var/lib/apt/lists; rm /opt/tmp/*; apt-get remove curl -y; apt-get autoremove -y

EXPOSE 5601

CMD sed -i "s|localhost|elasticsearch|g" /etc/service/kibana/config/kibana.yml && \
    /etc/service/kibana/bin/kibana
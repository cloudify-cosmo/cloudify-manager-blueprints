FROM cloudify_javabase:latest
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY ELASTICSEARCH_NOTICE.txt /root/ELASTICSEARCH_NOTICE.txt
COPY scripts/* /opt/scripts/

ENV ELASTICSEARCH_VERSION=1.4.3 \
    DOCKER_ENV=True \
    ELASTICSEARCH_HOME=/opt/elasticsearch \
    ES_JAVA_OPTS="-Xmx1024m -Xms1024m"

RUN apt-get update && \
    apt-get install -y curl && \
    curl --fail https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-${ELASTICSEARCH_VERSION}.tar.gz -o /tmp/elasticsearch.tar.gz && \
    mkdir -p ${ELASTICSEARCH_HOME} && \
    tar -C ${ELASTICSEARCH_HOME}/ -xvf /tmp/elasticsearch.tar.gz --strip-components=1 && \
    # start elasticsearch as daemon for configuration purposes.
    ${ELASTICSEARCH_HOME}/bin/elasticsearch -d && \
    chmod +x /opt/scripts/wait_for_port && sleep 3 && /opt/scripts/wait_for_port 9200 && \
    chmod +x /opt/scripts/configure_es && sleep 3 && /opt/scripts/configure_es && \
    mkdir -p /var/log/cloudify/elasticsearch && \
    rm -rf /var/lib/apt/lists && \
    rm -rf /tmp/* && \
    apt-get purge curl -y && \
    apt-get autoremove -y


COPY config/elasticsearch.yml ${ELASTICSEARCH_HOME}/config/elasticsearch.yml

VOLUME ${ELASTICSEARCH_HOME}/data

EXPOSE 9200

CMD ${ELASTICSEARCH_HOME}/bin/elasticsearch
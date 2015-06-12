FROM cloudify_javabase:latest
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY LOGSTASH_NOTICE.txt /root/LOGSTASH_NOTICE.txt

ENV LOGSTASH_VERSION=1.4.2 \
    DOCKER_ENV=True \
    LOGSTASH_HOME=/opt/logstash \
    LOGSTASH_LOG=/var/log/cloudify/logstash


RUN apt-get update && \
    mkdir -p ${LOGSTASH_LOG} && \
    mkdir -p ${LOGSTASH_HOME} && \
    apt-get install -y curl && \
    curl --fail --silent --location https://download.elasticsearch.org/logstash/logstash/logstash-${LOGSTASH_VERSION}.tar.gz -o /tmp/logstash.tar.gz && \
    tar -C ${LOGSTASH_HOME} -xzvf /tmp/logstash.tar.gz --strip-components=1 && \
    rm -rf /var/lib/apt/lists && \
    rm /tmp/* && \
    apt-get purge curl -y && \
    apt-get autoremove -y

RUN echo whatever && apt-get install what

COPY config/logstash.conf ${LOGSTASH_HOME}/logstash.conf

EXPOSE 9999

CMD ${LOGSTASH_HOME}/bin/logstash -f ${LOGSTASH_HOME}/logstash.conf -l ${LOGSTASH_LOG}/logstash.log --verbose
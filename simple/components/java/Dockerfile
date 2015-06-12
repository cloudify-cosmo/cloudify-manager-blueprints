FROM debian:jessie
MAINTAINER Gigaspaces, cosmo-admin@gigaspaces.com

COPY JAVABASE_NOTICE.txt /root/JAVABASE_NOTICE.txt

ENV JAVABASE_VERSION=7u76 \
    DOCKER_ENV=True \
    JAVA_HOME=/opt/java

RUN apt-get update && \
    apt-get install -y curl && \
    curl --fail --location --header "Cookie: oraclelicense=accept-securebackup-cookie" --create-dirs -o /tmp/java.tar.gz http://download.oracle.com/otn-pub/java/jdk/${JAVABASE_VERSION}-b13/jre-${JAVABASE_VERSION}-linux-x64.tar.gz && \
    mkdir ${JAVA_HOME} && tar -xzvf /tmp/java.tar.gz -C ${JAVA_HOME} --strip=1 && \
    rm -rf /var/lib/apt/lists && \
    rm /tmp/* && \
    apt-get purge curl -y && \
    apt-get autoremove -y